import re
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    GenerationScheduleRequest,
    PromptBuilder,
    ReasoningOutput,
)
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType, GenerationPayload
from app.domain.chat_context import ChatModeContext, GenerationIntent, OccasionContext
from app.domain.chat_modes import ChatMode, FlowState

from .constants import GENERATION_HINTS


class GenerationRequestBuilder:
    def __init__(self, *, prompt_builder: PromptBuilder | None = None) -> None:
        self.prompt_builder = prompt_builder or DefaultPromptBuilder()

    async def build_from_reasoning(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        reasoning_output: ReasoningOutput,
        asset_id: int | None,
        must_generate: bool,
        style_seed: dict[str, str] | None,
        occasion_context: OccasionContext | None,
        structured_outfit_brief: dict[str, Any] | None = None,
    ) -> DecisionResult:
        text_reply = reasoning_output.reply_text.strip()
        should_generate = self.resolve_should_generate(
            auto_generate=context.should_auto_generate,
            requested_route=reasoning_output.route,
            must_generate=must_generate,
        )
        if not should_generate:
            return DecisionResult(
                decision_type=DecisionType.TEXT_ONLY,
                active_mode=context.active_mode,
                flow_state=FlowState.COMPLETED,
                text_reply=text_reply,
            )

        image_brief_en = reasoning_output.image_brief_en.strip() or "cohesive editorial flat lay outfit"
        compiled_payload = await self.prompt_builder.build(
            brief={
                "user_message": command.normalized_message(),
                "image_brief_en": image_brief_en,
                "recommendation_text": text_reply,
                "asset_id": asset_id,
                "profile_context": command.profile_context,
                "style_seed": style_seed,
                "occasion_context": occasion_context.model_dump(exclude_none=True) if occasion_context else None,
                "structured_outfit_brief": structured_outfit_brief,
                "garment_outfit_brief": structured_outfit_brief,
            }
        )
        generation_intent = context.generation_intent or self.build_generation_intent(
            mode=context.active_mode,
            trigger=context.active_mode.value,
            reason="reasoning_requested_generation",
            must_generate=must_generate,
            source_message_id=command.user_message_id,
        )
        payload = GenerationPayload.model_validate(
            {
                **compiled_payload,
                "image_brief_en": compiled_payload.get("image_brief_en", image_brief_en),
                "recommendation_text": compiled_payload.get("recommendation_text", text_reply),
                "input_asset_id": compiled_payload.get("input_asset_id", asset_id),
                "generation_intent": generation_intent,
            }
        )
        decision = DecisionResult(
            decision_type=DecisionType.TEXT_AND_GENERATE,
            active_mode=context.active_mode,
            flow_state=FlowState.READY_FOR_GENERATION,
            text_reply=text_reply,
            generation_payload=payload,
        )
        return decision

    def build_schedule_request(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        decision: DecisionResult,
    ) -> GenerationScheduleRequest | None:
        generation_payload = decision.generation_payload
        if generation_payload is None:
            return None
        return GenerationScheduleRequest(
            session_id=command.session_id,
            locale=command.locale,
            input_text=command.normalized_message(),
            recommendation_text=decision.text_reply or generation_payload.recommendation_text,
            prompt=generation_payload.prompt,
            input_asset_id=generation_payload.input_asset_id,
            profile_context=command.profile_context,
            generation_intent=generation_payload.generation_intent,
            idempotency_key=command.build_generation_idempotency_key(active_mode=context.active_mode),
        )

    def build_clarification_decision(self, *, context: ChatModeContext, text: str) -> DecisionResult:
        return DecisionResult(
            decision_type=DecisionType.CLARIFICATION_REQUIRED,
            active_mode=context.active_mode,
            flow_state=context.flow_state,
            text_reply=text,
        )

    def build_recoverable_error(self, *, context: ChatModeContext, locale: str, error_code: str) -> DecisionResult:
        return DecisionResult(
            decision_type=DecisionType.ERROR_RECOVERABLE,
            active_mode=context.active_mode,
            flow_state=FlowState.RECOVERABLE_ERROR,
            text_reply=self.recoverable_error_text(locale),
            error_code=error_code,
        )

    def build_active_job_notice(self, *, context: ChatModeContext, locale: str) -> DecisionResult:
        notice = (
            "У вас уже есть активная генерация изображения. Дождитесь её завершения, и затем можно будет запустить следующую."
            if locale == "ru"
            else "You already have an active image generation task. Let it finish before starting the next one."
        )
        return DecisionResult(
            decision_type=DecisionType.TEXT_ONLY,
            active_mode=context.active_mode,
            flow_state=context.flow_state,
            text_reply=notice,
        )

    def build_generation_intent(
        self,
        *,
        mode: ChatMode,
        trigger: str,
        reason: str,
        must_generate: bool,
        source_message_id: int | None,
    ) -> GenerationIntent:
        return GenerationIntent(
            mode=mode,
            trigger=trigger,
            reason=reason,
            must_generate=must_generate,
            source_message_id=source_message_id,
        )

    def resolve_should_generate(self, *, auto_generate: bool, requested_route: str, must_generate: bool) -> bool:
        if must_generate:
            return True
        return auto_generate and requested_route == "text_and_generation"

    def explicitly_requests_generation(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in GENERATION_HINTS)

    def recoverable_error_text(self, locale: str) -> str:
        return (
            "Диалог получился слишком длинным для текущего шага. Попробуй переформулировать запрос короче или начни новый сценарий."
            if locale == "ru"
            else "This conversation became too long for the current step. Try a shorter request or start a new flow."
        )


class DefaultPromptBuilder:
    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        user_message = str(brief.get("user_message") or "")
        image_brief_en = str(brief.get("image_brief_en") or "")
        recommendation_text = str(brief.get("recommendation_text") or "")
        profile_context = brief.get("profile_context")
        asset_id = brief.get("asset_id")
        style_seed = brief.get("style_seed")
        occasion_context = brief.get("occasion_context")
        structured_outfit_brief = brief.get("structured_outfit_brief")
        garment_outfit_brief = brief.get("garment_outfit_brief") or structured_outfit_brief

        compact_brief = re.sub(r"\s+", " ", image_brief_en).strip() or "cohesive editorial outfit"
        compact_brief = " ".join(compact_brief.split()[:24])
        if isinstance(garment_outfit_brief, dict):
            brief_type = str(garment_outfit_brief.get("brief_type") or "").strip()
            if brief_type == "occasion_outfit":
                occasion_summary = str(garment_outfit_brief.get("occasion_summary") or "").strip()
                styling_goal = str(garment_outfit_brief.get("styling_goal") or "").strip()
                dressing_rules = "; ".join(str(item).strip() for item in garment_outfit_brief.get("dressing_rules", [])[:2])
                palette_direction = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("palette_direction", [])[:2]
                )
                footwear = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("footwear_guidance", [])[:2]
                )
                compact_brief = " ".join(
                    bit
                    for bit in [occasion_summary, styling_goal, dressing_rules, palette_direction, footwear]
                    if bit
                ).strip() or compact_brief
            else:
                anchor_summary = str(garment_outfit_brief.get("anchor_summary") or "").strip()
                styling_goal = str(garment_outfit_brief.get("styling_goal") or "").strip()
                complementary = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("complementary_garments", [])[:3]
                )
                footwear = "; ".join(str(item).strip() for item in garment_outfit_brief.get("footwear_options", [])[:2])
                negative_constraints = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("negative_constraints", [])[:2]
                )
                compact_brief = " ".join(
                    bit
                    for bit in [anchor_summary, styling_goal, complementary, footwear, negative_constraints]
                    if bit
                ).strip() or compact_brief
            compact_brief = " ".join(compact_brief.split()[:36])
        asset_part = f" Anchor around uploaded asset {asset_id}. " if asset_id else ""
        body_part = ""
        if isinstance(profile_context, dict):
            height_cm = self._coerce_int(profile_context.get("height_cm"))
            weight_kg = self._coerce_int(profile_context.get("weight_kg"))
            if height_cm or weight_kg:
                body_part = f" Proportion hint only: {height_cm or 'n/a'} cm, {weight_kg or 'n/a'} kg. "
            gender = self._optional_text(profile_context.get("gender"))
        else:
            gender = None
        gender_part = ""
        if gender == "male":
            gender_part = " Menswear proportions only; no womenswear garments or feminine-coded accessories. "
        elif gender == "female":
            gender_part = " Womenswear proportions only; no menswear-only tailoring cues or masculine-coded accessories. "
        style_part = ""
        if isinstance(style_seed, dict):
            title = str(style_seed.get("title") or "Style Direction")
            descriptor = str(style_seed.get("descriptor") or title)
            style_part = f" Style direction: {title}; {descriptor}. "
        occasion_part = ""
        if isinstance(occasion_context, dict):
            slots = [
                occasion_context.get("event_type"),
                occasion_context.get("time_of_day"),
                occasion_context.get("season"),
                occasion_context.get("dress_code") or occasion_context.get("desired_impression"),
            ]
            compact_slots = [str(slot).strip() for slot in slots if slot]
            if compact_slots:
                occasion_part = f" Occasion context: {'; '.join(compact_slots[:4])}. "
        garment_part = ""
        if isinstance(garment_outfit_brief, dict):
            brief_type = str(garment_outfit_brief.get("brief_type") or "").strip()
            garment_notes = []
            if brief_type == "occasion_outfit":
                for key in ("dressing_rules", "silhouette_notes", "layering_notes", "etiquette_notes"):
                    values = garment_outfit_brief.get(key)
                    if isinstance(values, list):
                        garment_notes.extend(str(value).strip() for value in values[:2] if str(value).strip())
                if garment_notes:
                    garment_part = f" Occasion brief: {'; '.join(garment_notes[:5])}. "
            else:
                for key in ("harmony_rules", "color_logic", "silhouette_balance", "tailoring_notes"):
                    values = garment_outfit_brief.get(key)
                    if isinstance(values, list):
                        garment_notes.extend(str(value).strip() for value in values[:2] if str(value).strip())
                if garment_notes:
                    garment_part = f" Garment brief: {'; '.join(garment_notes[:5])}. "
        request_part = re.sub(r"\s+", " ", user_message).strip()
        request_text = f" User context: {' '.join(request_part.split()[:12])}. " if request_part else ""
        prompt = (
            "Luxury editorial flat lay, overhead, garments only; no model, mannequin, body parts, text, logos, collage, props, hanger, or watermark. "
            "One complete outfit only, 4 to 6 items max, fully visible, coherent, and readable. "
            "No duplicate categories, broken tailoring, clutter, or floating extras. "
            f"Brief: {compact_brief}. "
            f"{request_text}{occasion_part}{garment_part}{asset_part}{body_part}{gender_part}{style_part}"
        ).strip()
        return {
            "prompt": " ".join(prompt.split()[:95]),
            "image_brief_en": image_brief_en,
            "recommendation_text": recommendation_text,
            "input_asset_id": asset_id,
        }

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None
