import re
from typing import Any

from app.application.product_behavior.services.generation_policy_service import (
    GenerationPolicyInput,
    GenerationPolicyService,
)
from app.application.prompt_building.services.prompt_pipeline_builder import (
    PromptPipelineBuilder,
    PromptPipelineValidationError,
)
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
from .style_prompt_compiler import StylePromptCompiler


class GenerationRequestBuilder:
    def __init__(
        self,
        *,
        prompt_builder: PromptBuilder | None = None,
        generation_policy_service: GenerationPolicyService | None = None,
    ) -> None:
        self.prompt_builder = prompt_builder or DefaultPromptBuilder()
        self.generation_policy_service = generation_policy_service or GenerationPolicyService()

    async def build_from_reasoning(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        reasoning_output: ReasoningOutput,
        asset_id: int | None,
        must_generate: bool,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, object]] | None,
        occasion_context: OccasionContext | None,
        anti_repeat_constraints: dict[str, object] | None,
        structured_outfit_brief: dict[str, Any] | None = None,
        knowledge_cards: list[dict[str, Any]] | None = None,
        knowledge_bundle: dict[str, Any] | None = None,
        knowledge_provider_used: str | None = None,
    ) -> DecisionResult:
        text_reply = reasoning_output.reply_text.strip()
        generation_decision = await self.generation_policy_service.decide(
            GenerationPolicyInput(
                command=command,
                context=context,
                reasoning_output=reasoning_output,
                must_generate=must_generate,
                has_visualizable_brief=structured_outfit_brief is not None,
            )
        )
        if not generation_decision.should_generate:
            decision = DecisionResult(
                decision_type=DecisionType.TEXT_ONLY,
                active_mode=context.active_mode,
                flow_state=FlowState.COMPLETED,
                text_reply=text_reply,
            )
            decision.apply_visualization_offer(generation_decision.to_offer())
            return decision

        image_brief_en = reasoning_output.image_brief_en.strip() or "cohesive editorial flat lay outfit"
        try:
            compiled_payload = await self.prompt_builder.build(
                brief={
                    "session_id": command.session_id,
                    "message_id": command.user_message_id,
                    "mode": context.active_mode.value,
                    "user_message": command.normalized_message(),
                    "image_brief_en": image_brief_en,
                    "recommendation_text": text_reply,
                    "asset_id": asset_id,
                    "profile_context": command.profile_context,
                    "style_seed": style_seed,
                    "previous_style_directions": previous_style_directions or [],
                    "anti_repeat_constraints": anti_repeat_constraints or {},
                    "occasion_context": occasion_context.model_dump(exclude_none=True) if occasion_context else None,
                    "structured_outfit_brief": structured_outfit_brief,
                    "garment_outfit_brief": structured_outfit_brief,
                    "style_exploration_brief": (
                        structured_outfit_brief
                        if isinstance(structured_outfit_brief, dict)
                        and str(structured_outfit_brief.get("brief_type") or "").strip() == "style_exploration"
                        else None
                    ),
                    "knowledge_cards": knowledge_cards or [],
                    "knowledge_bundle": knowledge_bundle,
                    "knowledge_provider_used": knowledge_provider_used,
                }
            )
        except PromptPipelineValidationError as exc:
            decision = self.build_recoverable_error(
                context=context,
                locale=command.locale,
                error_code="prompt_validation_failed",
            )
            decision.telemetry.update(
                {
                    "validation_errors": list(exc.errors),
                    "validation_errors_count": len(exc.errors),
                }
            )
            return decision
        generation_intent = context.generation_intent or self.build_generation_intent(
            mode=context.active_mode,
            trigger=self._resolve_generation_trigger(command=command, context=context),
            reason=generation_decision.reason,
            must_generate=True,
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
        decision.apply_visualization_offer(generation_decision.to_offer())
        if isinstance(payload.metadata, dict):
            for key in (
                "brief_hash",
                "compiled_prompt_hash",
                "diversity_constraints_hash",
                "knowledge_cards_count",
                "knowledge_bundle_hash",
                "knowledge_query_hash",
                "validation_errors_count",
                "workflow_name",
                "workflow_version",
                "retrieved_style_cards_count",
                "retrieved_color_cards_count",
                "retrieved_history_cards_count",
                "retrieved_tailoring_cards_count",
                "retrieved_material_cards_count",
                "retrieved_flatlay_cards_count",
                "layout_archetype",
                "background_family",
                "object_count_range",
                "spacing_density",
                "camera_distance",
                "shadow_hardness",
                "anchor_garment_centrality",
                "practical_coherence",
            ):
                if key in payload.metadata:
                    decision.telemetry[key] = payload.metadata[key]
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
        schedule_metadata = dict(generation_payload.metadata)
        for key in ("usage_subject_id", "usage_session_id", "usage_user_id", "usage_is_admin"):
            if key in command.metadata and key not in schedule_metadata:
                schedule_metadata[key] = command.metadata[key]
        return GenerationScheduleRequest(
            session_id=command.session_id,
            locale=command.locale,
            input_text=command.normalized_message(),
            recommendation_text=decision.text_reply or generation_payload.recommendation_text,
            prompt=generation_payload.prompt,
            negative_prompt=generation_payload.negative_prompt,
            input_asset_id=generation_payload.input_asset_id,
            profile_context=command.profile_context,
            generation_intent=generation_payload.generation_intent,
            idempotency_key=command.build_generation_idempotency_key(active_mode=context.active_mode),
            workflow_name=generation_payload.metadata.get("workflow_name"),
            workflow_version=generation_payload.metadata.get("workflow_version"),
            visual_generation_plan=generation_payload.visual_generation_plan,
            generation_metadata=generation_payload.generation_metadata,
            metadata=schedule_metadata,
            request_metadata=dict(command.request_metadata),
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

    def downgrade_generation_to_text_only(
        self,
        *,
        decision: DecisionResult,
        context: ChatModeContext,
        notice_text: str,
        replace_text: bool = False,
    ) -> DecisionResult:
        base_text = "" if replace_text else self._remove_generation_launch_promises(decision.text_reply or "")
        notice = notice_text.strip()
        if base_text and notice and notice not in base_text:
            text_reply = f"{base_text}\n\n{notice}"
        else:
            text_reply = base_text or notice
        downgraded = decision.model_copy(deep=True)
        downgraded.decision_type = DecisionType.TEXT_ONLY
        downgraded.flow_state = context.flow_state
        downgraded.text_reply = text_reply
        downgraded.generation_payload = None
        downgraded.job_id = None
        downgraded.visualization_offer = None
        downgraded.can_offer_visualization = False
        downgraded.cta_text = None
        downgraded.visualization_type = None
        return downgraded

    def _remove_generation_launch_promises(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        cleaned = re.sub(
            r"\s+и\s+запускаю\s+(?:визуализацию|генерацию)\.?",
            ".",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\s+and\s+(?:i\s+)?(?:will|am\s+going\s+to)\s+(?:visualize|generate)\s+(?:it|this)?(?:\s+now)?\.?",
            ".",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"\.{2,}$", ".", cleaned)
        return cleaned

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

    def explicitly_requests_generation(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in GENERATION_HINTS)

    def _resolve_generation_trigger(self, *, command: ChatCommand, context: ChatModeContext) -> str:
        if command.source == "quick_action" and command.command_name == ChatMode.STYLE_EXPLORATION.value:
            return ChatMode.STYLE_EXPLORATION.value
        if command.source in {"visualization_cta", "explicit_visual_request"}:
            return command.source
        if self.explicitly_requests_generation(command.normalized_message()):
            return "explicit_visual_request"
        return context.active_mode.value

    def recoverable_error_text(self, locale: str) -> str:
        return (
            "Диалог получился слишком длинным для текущего шага. Попробуй переформулировать запрос короче или начни новый сценарий."
            if locale == "ru"
            else "This conversation became too long for the current step. Try a shorter request or start a new flow."
        )


class DefaultPromptBuilder:
    def __init__(self) -> None:
        self.prompt_pipeline_builder = PromptPipelineBuilder()

    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        return await self.prompt_pipeline_builder.build(brief=brief)

    async def build_legacy(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        user_message = str(brief.get("user_message") or "")
        image_brief_en = str(brief.get("image_brief_en") or "")
        recommendation_text = str(brief.get("recommendation_text") or "")
        profile_context = brief.get("profile_context")
        asset_id = brief.get("asset_id")
        style_seed = brief.get("style_seed")
        previous_style_directions = brief.get("previous_style_directions") or []
        anti_repeat_constraints = brief.get("anti_repeat_constraints") or {}
        occasion_context = brief.get("occasion_context")
        structured_outfit_brief = brief.get("structured_outfit_brief")
        garment_outfit_brief = brief.get("garment_outfit_brief") or structured_outfit_brief
        style_exploration_brief = brief.get("style_exploration_brief")

        if isinstance(style_exploration_brief, dict):
            return await StylePromptCompiler().build(
                brief={
                    **brief,
                    "style_exploration_brief": style_exploration_brief,
                    "previous_style_directions": previous_style_directions,
                    "anti_repeat_constraints": anti_repeat_constraints,
                }
            )

        compact_brief = re.sub(r"\s+", " ", image_brief_en).strip() or "cohesive editorial outfit"
        compact_brief = " ".join(compact_brief.split()[:24])
        if isinstance(garment_outfit_brief, dict):
            brief_type = str(garment_outfit_brief.get("brief_type") or "").strip()
            if brief_type == "occasion_outfit":
                styling_goal = str(garment_outfit_brief.get("styling_goal") or "").strip()
                dress_code_logic = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("dress_code_logic", [])[:2]
                )
                garment_recommendations = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("garment_recommendations", [])[:2]
                )
                color_logic = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("color_logic", [])[:2]
                )
                footwear = "; ".join(
                    str(item).strip() for item in garment_outfit_brief.get("footwear_recommendations", [])[:2]
                )
                compact_brief = " ".join(
                    bit
                    for bit in [styling_goal, dress_code_logic, garment_recommendations, color_logic, footwear]
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
                for key in (
                    "dress_code_logic",
                    "impression_logic",
                    "silhouette_logic",
                    "tailoring_notes",
                    "negative_constraints",
                ):
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
            "metadata": {},
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
