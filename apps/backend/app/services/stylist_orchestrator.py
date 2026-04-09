import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_context import (
    AnchorGarment,
    ChatModeContext,
    GenerationIntent,
    OccasionContext,
    StyleDirectionContext,
)
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState
from app.domain.decision_result import DecisionResult, DecisionType, GenerationPayload
from app.domain.state_machine.garment_matching_machine import GarmentMatchingStateMachine
from app.domain.state_machine.general_advice_machine import GeneralAdviceStateMachine
from app.domain.state_machine.occasion_outfit_machine import OccasionOutfitStateMachine
from app.domain.state_machine.style_exploration_machine import StyleExplorationStateMachine
from app.models import StyleDirection, UploadedAsset
from app.models.chat_message import ChatMessage
from app.repositories.style_directions import style_directions_repository
from app.repositories.stylist_style_exposures import stylist_style_exposures_repository
from app.services.chat_mode_resolver import ModeResolution

try:
    from app.integrations.vllm import VLLMClient, VLLMClientError, VLLMContextLimitError
except ModuleNotFoundError:
    VLLMClient = None

    class VLLMClientError(RuntimeError):
        pass

    class VLLMContextLimitError(VLLMClientError):
        pass


class _UnavailableVLLMClient:
    async def generate_stylist_response(self, **_: object):
        raise VLLMClientError("vLLM client dependencies are unavailable in this environment")

    async def extract_occasion_slots(self, **_: object):
        raise VLLMClientError("vLLM client dependencies are unavailable in this environment")

logger = logging.getLogger(__name__)

GENERATION_HINTS = (
    "generate",
    "render",
    "visualize",
    "visualise",
    "lookbook",
    "flat lay",
    "flat-lay",
    "сгенер",
    "визуал",
    "покажи",
)

GARMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shirt": ("shirt", "рубаш"),
    "t-shirt": ("t-shirt", "tee", "футболк"),
    "blazer": ("blazer", "пиджак"),
    "jacket": ("jacket", "куртк"),
    "coat": ("coat", "пальто", "тренч"),
    "hoodie": ("hoodie", "толстовк", "худи"),
    "sweater": ("sweater", "jumper", "пуловер", "свитер"),
    "dress": ("dress", "плать"),
    "skirt": ("skirt", "юбк"),
    "trousers": ("trousers", "pants", "брюк"),
    "jeans": ("jeans", "джинс"),
    "sneakers": ("sneakers", "кроссовк"),
    "shoes": ("shoes", "boots", "ботин", "туфл"),
    "bag": ("bag", "сумк"),
}

COLOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "black": ("black", "черн"),
    "white": ("white", "бел"),
    "grey": ("grey", "gray", "сер"),
    "navy": ("navy", "темно-син", "тёмно-син"),
    "blue": ("blue", "син"),
    "beige": ("beige", "беж"),
    "brown": ("brown", "корич"),
    "green": ("green", "зелен", "зелён"),
    "red": ("red", "красн"),
}

MATERIAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "denim": ("denim", "джинс"),
    "linen": ("linen", "лен", "лён"),
    "cotton": ("cotton", "хлоп"),
    "wool": ("wool", "шерст"),
    "leather": ("leather", "кож"),
    "suede": ("suede", "замш"),
    "knit": ("knit", "трикот"),
}

FIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "straight": ("straight", "прям"),
    "slim": ("slim", "притал"),
    "oversized": ("oversized", "оверсайз"),
    "relaxed": ("relaxed", "свобод"),
}

SEASON_KEYWORDS: dict[str, tuple[str, ...]] = {
    "spring": ("spring", "весн"),
    "summer": ("summer", "лет"),
    "autumn": ("autumn", "fall", "осен"),
    "winter": ("winter", "зим"),
}

TIME_OF_DAY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "morning": ("morning", "утр"),
    "day": ("day", "днем", "днём", "день"),
    "evening": ("evening", "вечер"),
    "night": ("night", "ноч"),
}

DRESS_CODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "black tie": ("black tie",),
    "cocktail": ("cocktail", "коктейл"),
    "formal": ("formal", "формаль"),
    "smart casual": ("smart casual", "smart-casual", "смарт"),
    "casual": ("casual", "кэжуал", "повседнев"),
}

EVENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "wedding": ("wedding", "свад"),
    "date": ("date", "свидан"),
    "dinner": ("dinner", "ужин"),
    "office party": ("corporate", "корпоратив", "office party"),
    "theater": ("theater", "theatre", "театр"),
    "party": ("party", "вечерин"),
    "conference": ("conference", "конферен"),
    "birthday": ("birthday", "день рождения"),
}

IMPRESSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "elegant": ("elegant", "элегант"),
    "confident": ("confident", "уверен"),
    "romantic": ("romantic", "романт"),
    "relaxed": ("relaxed", "расслаб"),
    "bold": ("bold", "смел"),
}

LOCATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "restaurant": ("restaurant", "ресторан"),
    "outdoor": ("outdoor", "outside", "open air", "на улице"),
    "office": ("office", "офис"),
    "theater": ("theater", "theatre", "театр"),
    "beach": ("beach", "пляж"),
}

WEATHER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cold": ("cold", "холод"),
    "warm": ("warm", "тепл", "тёпл"),
    "hot": ("hot", "жарк"),
    "rainy": ("rain", "rainy", "дожд"),
    "windy": ("wind", "ветр"),
}

FALLBACK_STYLE_LIBRARY: tuple[dict[str, Any], ...] = (
    {
        "style_id": "artful-minimalism",
        "style_name": "Artful Minimalism",
        "palette": ["chalk", "charcoal", "stone"],
        "silhouette": "clean and elongated",
        "hero_garments": ["structured coat", "fine knit", "straight trousers"],
        "footwear": ["sharp leather shoes"],
        "accessories": ["restrained watch"],
        "materials": ["wool", "cotton"],
        "styling_mood": "quiet and precise",
        "composition_type": "editorial flat lay",
        "background_family": "stone",
    },
    {
        "style_id": "soft-retro-prep",
        "style_name": "Soft Retro Prep",
        "palette": ["camel", "cream", "navy"],
        "silhouette": "relaxed collegiate layering",
        "hero_garments": ["oxford shirt", "textured knit", "pleated trousers"],
        "footwear": ["loafers"],
        "accessories": ["belt"],
        "materials": ["tweed", "cotton"],
        "styling_mood": "polished but warm",
        "composition_type": "editorial flat lay",
        "background_family": "paper",
    },
    {
        "style_id": "relaxed-workwear",
        "style_name": "Relaxed Workwear",
        "palette": ["olive", "ecru", "brown"],
        "silhouette": "grounded utility layers",
        "hero_garments": ["overshirt", "sturdy trousers", "simple tee"],
        "footwear": ["substantial boots"],
        "accessories": ["canvas belt"],
        "materials": ["canvas", "denim"],
        "styling_mood": "practical and calm",
        "composition_type": "editorial flat lay",
        "background_family": "wood",
    },
)


class StylistChatOrchestrator:
    def __init__(self) -> None:
        self.vllm_client = VLLMClient() if VLLMClient is not None else _UnavailableVLLMClient()

    async def plan_turn(
        self,
        *,
        session: AsyncSession,
        session_id: str,
        locale: str,
        context: ChatModeContext,
        resolution: ModeResolution,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
    ) -> tuple[ChatModeContext, DecisionResult]:
        next_context = context
        if resolution.started_new_mode:
            next_context = context.reset_for_mode(
                mode=resolution.active_mode,
                requested_intent=resolution.requested_intent,
                should_auto_generate=resolution.active_mode != ChatMode.GENERAL_ADVICE,
                command_context=resolution.command_context,
            )
        else:
            next_context.active_mode = resolution.active_mode
            next_context.requested_intent = resolution.requested_intent
            next_context.command_context = resolution.command_context
            next_context.should_auto_generate = resolution.active_mode != ChatMode.GENERAL_ADVICE

        next_context.remember(role="user", content=user_message)

        if resolution.active_mode == ChatMode.GARMENT_MATCHING:
            decision = await self._plan_garment_matching(
                locale=locale,
                context=next_context,
                user_message=user_message,
                user_message_id=user_message_id,
                asset=asset,
                recent_messages=recent_messages,
                profile_context=profile_context,
            )
        elif resolution.active_mode == ChatMode.OCCASION_OUTFIT:
            decision = await self._plan_occasion_outfit(
                locale=locale,
                context=next_context,
                user_message=user_message,
                user_message_id=user_message_id,
                asset=asset,
                recent_messages=recent_messages,
                profile_context=profile_context,
            )
        elif resolution.active_mode == ChatMode.STYLE_EXPLORATION:
            decision = await self._plan_style_exploration(
                session=session,
                session_id=session_id,
                locale=locale,
                context=next_context,
                user_message=user_message,
                user_message_id=user_message_id,
                asset=asset,
                recent_messages=recent_messages,
                profile_context=profile_context,
            )
        else:
            decision = await self._plan_general_advice(
                locale=locale,
                context=next_context,
                user_message=user_message,
                user_message_id=user_message_id,
                asset=asset,
                recent_messages=recent_messages,
                profile_context=profile_context,
            )

        next_context.last_decision_type = decision.decision_type.value
        next_context.touch(message_id=user_message_id)
        decision.context_patch = self._build_context_patch(next_context)
        return next_context, decision

    async def _plan_general_advice(
        self,
        *,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
    ) -> DecisionResult:
        GeneralAdviceStateMachine.enter(context)
        GeneralAdviceStateMachine.accept_user_message(context)
        decision = await self._build_generation_capable_decision(
            locale=locale,
            context=context,
            user_message=user_message,
            user_message_id=user_message_id,
            asset=asset,
            recent_messages=recent_messages,
            profile_context=profile_context,
            auto_generate=self._explicitly_requests_generation(user_message),
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
        )
        if decision.requires_generation():
            context.should_auto_generate = True
            context.flow_state = FlowState.READY_FOR_GENERATION
        else:
            GeneralAdviceStateMachine.complete(context)
        return decision

    async def _plan_garment_matching(
        self,
        *,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
    ) -> DecisionResult:
        entry_prompt = self._garment_entry_prompt(locale)
        if context.flow_state in {FlowState.IDLE, FlowState.COMPLETED, FlowState.RECOVERABLE_ERROR}:
            GarmentMatchingStateMachine.enter(context, prompt_text=entry_prompt)

        anchor = self._extract_anchor_garment(user_message=user_message, asset=asset, profile_context=profile_context)
        if not anchor.raw_user_text and asset is None:
            return self._build_clarification_decision(context=context, text=entry_prompt)

        clarification_text = None if anchor.is_sufficient_for_generation else self._garment_clarification_prompt(locale, anchor)
        GarmentMatchingStateMachine.consume_anchor_garment(
            context,
            anchor_garment=anchor,
            clarification_text=clarification_text,
        )
        if context.flow_state == FlowState.AWAITING_CLARIFICATION:
            return self._build_clarification_decision(context=context, text=context.pending_clarification or entry_prompt)

        GarmentMatchingStateMachine.mark_ready_for_generation(context)
        decision = await self._build_generation_capable_decision(
            locale=locale,
            context=context,
            user_message=anchor.raw_user_text or user_message,
            user_message_id=user_message_id,
            asset=asset,
            recent_messages=recent_messages,
            profile_context=profile_context,
            auto_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
        )
        context.generation_intent = self._build_generation_intent(
            mode=ChatMode.GARMENT_MATCHING,
            trigger="garment_matching",
            reason="anchor_garment_is_sufficient_for_generation",
            must_generate=True,
            source_message_id=user_message_id,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision

    async def _plan_occasion_outfit(
        self,
        *,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
    ) -> DecisionResult:
        entry_prompt = self._occasion_entry_prompt(locale)
        if context.flow_state in {FlowState.IDLE, FlowState.COMPLETED, FlowState.RECOVERABLE_ERROR}:
            OccasionOutfitStateMachine.enter(context, prompt_text=entry_prompt)

        occasion_context = await self._extract_occasion_context(
            locale=locale,
            user_message=user_message,
            recent_messages=recent_messages,
            existing_context=context.occasion_context,
        )
        clarification_kind, clarification_text = self._occasion_clarification(locale, occasion_context)
        OccasionOutfitStateMachine.consume_occasion_context(
            context,
            occasion_context=occasion_context,
            clarification_kind=clarification_kind,
            clarification_text=clarification_text,
        )
        if context.flow_state == FlowState.AWAITING_CLARIFICATION:
            return self._build_clarification_decision(context=context, text=context.pending_clarification or entry_prompt)

        OccasionOutfitStateMachine.mark_ready_for_generation(context)
        decision = await self._build_generation_capable_decision(
            locale=locale,
            context=context,
            user_message=user_message,
            user_message_id=user_message_id,
            asset=asset,
            recent_messages=recent_messages,
            profile_context=profile_context,
            auto_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=occasion_context,
        )
        context.generation_intent = self._build_generation_intent(
            mode=ChatMode.OCCASION_OUTFIT,
            trigger="occasion_outfit",
            reason="occasion_context_has_required_slots",
            must_generate=True,
            source_message_id=user_message_id,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision

    async def _plan_style_exploration(
        self,
        *,
        session: AsyncSession,
        session_id: str,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
    ) -> DecisionResult:
        StyleExplorationStateMachine.enter(context)
        previous_style_directions = self._style_history_to_prompt(context.style_history)
        style_context, style_model = await self._pick_style_direction(
            session=session,
            session_id=session_id,
            style_history=context.style_history,
        )
        StyleExplorationStateMachine.select_style(context, style=style_context)
        if style_model is not None:
            await self._record_style_exposure(session, session_id, style_model)
        StyleExplorationStateMachine.mark_ready_for_generation(context)

        decision = await self._build_generation_capable_decision(
            locale=locale,
            context=context,
            user_message=user_message or ("Новый стиль" if locale == "ru" else "Try another style"),
            user_message_id=user_message_id,
            asset=asset,
            recent_messages=recent_messages,
            profile_context=profile_context,
            auto_generate=True,
            style_seed=self._style_seed_from_context(style_context),
            previous_style_directions=previous_style_directions,
            occasion_context=None,
        )
        context.generation_intent = self._build_generation_intent(
            mode=ChatMode.STYLE_EXPLORATION,
            trigger="style_exploration",
            reason="new_style_direction_selected",
            must_generate=True,
            source_message_id=user_message_id,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision

    async def _build_generation_capable_decision(
        self,
        *,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        recent_messages: list[ChatMessage],
        profile_context: dict[str, str | int | None],
        auto_generate: bool,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, str]],
        occasion_context: OccasionContext | None,
    ) -> DecisionResult:
        try:
            result = await self.vllm_client.generate_stylist_response(
                locale=locale,
                user_message=user_message,
                uploaded_asset_name=asset.original_filename if asset else None,
                body_height_cm=self._coerce_int(profile_context.get("height_cm")),
                body_weight_kg=self._coerce_int(profile_context.get("weight_kg")),
                auto_generate=auto_generate,
                conversation_history=self._build_conversation_history(recent_messages),
                profile_context=profile_context,
                session_intent=context.active_mode.value,
                style_seed=style_seed,
                previous_style_directions=previous_style_directions,
                occasion_context=occasion_context.model_dump(exclude_none=True) if occasion_context else None,
            )
            should_generate = self._resolve_should_generate(
                mode=context.active_mode,
                requested_route=result.route,
                auto_generate=auto_generate,
            )
            generation_payload = None
            decision_type = DecisionType.TEXT_ONLY
            if should_generate:
                generation_payload = GenerationPayload(
                    prompt=self._build_generation_prompt(
                        user_message=user_message,
                        image_brief_en=result.image_brief_en,
                        asset=asset,
                        profile_context=profile_context,
                        style_seed=style_seed,
                        occasion_context=occasion_context,
                    ),
                    image_brief_en=result.image_brief_en,
                    recommendation_text=result.reply_text,
                    input_asset_id=asset.id if asset else None,
                    generation_intent=self._build_generation_intent(
                        mode=context.active_mode,
                        trigger=context.active_mode.value,
                        reason="decision_layer_requested_generation",
                        must_generate=context.active_mode != ChatMode.GENERAL_ADVICE,
                        source_message_id=user_message_id,
                    ),
                )
                decision_type = DecisionType.TEXT_AND_GENERATE
            return DecisionResult(
                decision_type=decision_type,
                active_mode=context.active_mode,
                flow_state=context.flow_state,
                text_reply=result.reply_text,
                generation_payload=generation_payload,
            )
        except VLLMContextLimitError as exc:
            logger.warning("vLLM context limit reached for stylist turn: %s", exc)
            return DecisionResult(
                decision_type=DecisionType.ERROR_RECOVERABLE,
                active_mode=context.active_mode,
                flow_state=FlowState.RECOVERABLE_ERROR,
                text_reply=self._recoverable_error_text(locale),
                error_code="context_limit",
            )
        except VLLMClientError as exc:
            logger.warning("vLLM is unavailable, using deterministic fallback: %s", exc)
            return self._build_fallback_decision(
                locale=locale,
                context=context,
                user_message=user_message,
                user_message_id=user_message_id,
                asset=asset,
                profile_context=profile_context,
                style_seed=style_seed,
                occasion_context=occasion_context,
                auto_generate=auto_generate,
            )

    def _build_fallback_decision(
        self,
        *,
        locale: str,
        context: ChatModeContext,
        user_message: str,
        user_message_id: int,
        asset: UploadedAsset | None,
        profile_context: dict[str, str | int | None],
        style_seed: dict[str, str] | None,
        occasion_context: OccasionContext | None,
        auto_generate: bool,
    ) -> DecisionResult:
        if context.active_mode == ChatMode.GARMENT_MATCHING:
            anchor_name = context.anchor_garment.garment_type if context.anchor_garment else None
            reply_text = (
                f"Собираю образ вокруг вещи: {anchor_name or 'вашей вещи'}. Оставлю один цельный комплект, чтобы главный предмет не потерялся."
                if locale == "ru"
                else f"I am building the look around {anchor_name or 'your garment'}. I will keep it to one coherent outfit so the anchor piece stays clear."
            )
            brief = f"coherent outfit built around {anchor_name or 'the anchor garment'}, restrained styling, clear focal piece"
        elif context.active_mode == ChatMode.OCCASION_OUTFIT and occasion_context is not None:
            occasion_name = occasion_context.event_type or "the event"
            reply_text = (
                f"Собираю уместный образ для события: {occasion_name}. Сохраню аккуратную стилистику и читаемый уровень формальности."
                if locale == "ru"
                else f"I am building an event-aware outfit for {occasion_name}. I will keep the styling polished and the formality level clear."
            )
            brief = f"event-aware outfit for {occasion_name}, polished flat lay, clean wardrobe logic"
        elif context.active_mode == ChatMode.STYLE_EXPLORATION and style_seed is not None:
            reply_text = (
                f"Переключаю образ в направление {style_seed['title']}. Сделаю новый стиль отличимым не только цветом, но и логикой вещей."
                if locale == "ru"
                else f"I am switching the look into the {style_seed['title']} direction. The new style will feel different in both palette and garment logic."
            )
            brief = f"{style_seed['title']}, {style_seed['descriptor']}, one coherent editorial flat lay outfit"
        else:
            reply_text = (
                "Я дам практичную стилистическую рекомендацию без лишней театральности."
                if locale == "ru"
                else "I will keep the recommendation practical, concise, and wearable."
            )
            brief = "cohesive editorial outfit, calm palette, practical styling logic"

        should_generate = self._resolve_should_generate(
            mode=context.active_mode,
            requested_route="text_and_generation" if auto_generate else "text_only",
            auto_generate=auto_generate,
        )
        generation_payload = None
        decision_type = DecisionType.TEXT_ONLY
        if should_generate:
            generation_payload = GenerationPayload(
                prompt=self._build_generation_prompt(
                    user_message=user_message,
                    image_brief_en=brief,
                    asset=asset,
                    profile_context=profile_context,
                    style_seed=style_seed,
                    occasion_context=occasion_context,
                ),
                image_brief_en=brief,
                recommendation_text=reply_text,
                input_asset_id=asset.id if asset else None,
                generation_intent=self._build_generation_intent(
                    mode=context.active_mode,
                    trigger=context.active_mode.value,
                    reason="fallback_generation_path",
                    must_generate=context.active_mode != ChatMode.GENERAL_ADVICE,
                    source_message_id=user_message_id,
                ),
            )
            decision_type = DecisionType.TEXT_AND_GENERATE
        return DecisionResult(
            decision_type=decision_type,
            active_mode=context.active_mode,
            flow_state=context.flow_state,
            text_reply=reply_text,
            generation_payload=generation_payload,
        )

    def _build_clarification_decision(self, *, context: ChatModeContext, text: str) -> DecisionResult:
        return DecisionResult(
            decision_type=DecisionType.CLARIFICATION_REQUIRED,
            active_mode=context.active_mode,
            flow_state=context.flow_state,
            text_reply=text,
        )

    def _build_generation_intent(
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
            job_priority="normal",
            source_message_id=source_message_id,
        )

    def _resolve_should_generate(self, *, mode: ChatMode, requested_route: str, auto_generate: bool) -> bool:
        if mode in {ChatMode.GARMENT_MATCHING, ChatMode.STYLE_EXPLORATION, ChatMode.OCCASION_OUTFIT}:
            return requested_route != "text_and_catalog"
        return auto_generate and requested_route == "text_and_generation"

    def _garment_entry_prompt(self, locale: str) -> str:
        return (
            "Опиши вещь, вокруг которой нужно собрать образ: что это за предмет, какого он цвета, из какого материала и как сидит."
            if locale == "ru"
            else "Describe the garment you want to build the outfit around: what it is, the color, the material, and the fit."
        )

    def _garment_clarification_prompt(self, locale: str, anchor: AnchorGarment) -> str:
        if not anchor.garment_type:
            return (
                "Уточни, пожалуйста, что это за вещь: рубашка, жакет, платье, брюки, обувь или что-то другое."
                if locale == "ru"
                else "Please clarify what kind of garment it is: a shirt, jacket, dress, trousers, shoes, or something else."
            )
        return (
            "Добавь один-два признака вещи: цвет, материал или посадку. Этого достаточно, чтобы собрать цельный образ."
            if locale == "ru"
            else "Add one or two garment details such as the color, material, or fit. That is enough for me to build a coherent look."
        )

    def _occasion_entry_prompt(self, locale: str) -> str:
        return (
            "Расскажи, пожалуйста, что это за событие, в какое время суток оно проходит, какой сейчас сезон и есть ли dress code или желаемое впечатление."
            if locale == "ru"
            else "Tell me what kind of event it is, what time of day it happens, what season it is, and whether there is a dress code or a desired impression."
        )

    def _occasion_clarification(
        self,
        locale: str,
        occasion_context: OccasionContext,
    ) -> tuple[ClarificationKind | None, str | None]:
        missing = occasion_context.missing_core_slots()
        if not missing:
            return None, None
        if missing[0] == "event_type":
            return (
                ClarificationKind.OCCASION_EVENT_TYPE,
                "Что это за событие: свадьба, свидание, ужин, театр, вечеринка или что-то другое?"
                if locale == "ru"
                else "What kind of event is it: a wedding, date, dinner, theater night, party, or something else?",
            )
        if missing == ["dress_code_or_desired_impression"]:
            return (
                ClarificationKind.OCCASION_DRESS_CODE,
                "Есть ли dress code или образ, который ты хочешь производить: более элегантный, расслабленный, заметный?"
                if locale == "ru"
                else "Is there a dress code or a specific impression you want to create, such as elegant, relaxed, or striking?",
            )
        return (
            ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS,
            "Мне нужно ещё немного контекста: событие, время суток, сезон и хотя бы dress code или желаемое впечатление."
            if locale == "ru"
            else "I still need a bit more context: the event type, the time of day, the season, and at least a dress code or a desired impression.",
        )

    def _extract_anchor_garment(
        self,
        *,
        user_message: str,
        asset: UploadedAsset | None,
        profile_context: dict[str, str | int | None],
    ) -> AnchorGarment:
        raw_text = user_message.strip()
        if not raw_text and asset is not None:
            raw_text = asset.original_filename
        lowered = raw_text.lower()

        garment_type = self._first_keyword_match(lowered, GARMENT_KEYWORDS)
        colors = self._all_keyword_matches(lowered, COLOR_KEYWORDS)
        material = self._first_keyword_match(lowered, MATERIAL_KEYWORDS)
        fit = self._first_keyword_match(lowered, FIT_KEYWORDS)
        seasonality = self._first_keyword_match(lowered, SEASON_KEYWORDS)
        confidence = 0.1
        confidence += 0.35 if garment_type else 0.0
        confidence += 0.15 if colors else 0.0
        confidence += 0.15 if material else 0.0
        confidence += 0.15 if fit else 0.0
        confidence += 0.2 if asset is not None else 0.0
        return AnchorGarment(
            raw_user_text=raw_text or None,
            garment_type=garment_type,
            color=colors[0] if colors else None,
            secondary_colors=colors[1:] if len(colors) > 1 else [],
            material=material,
            fit=fit,
            silhouette=fit,
            seasonality=seasonality,
            formality=self._infer_formality(lowered),
            gender_context=self._optional_text(profile_context.get("gender")),
            confidence=min(confidence, 0.95),
            is_sufficient_for_generation=bool(asset is not None or (garment_type and (colors or material or fit))),
        )

    async def _extract_occasion_context(
        self,
        *,
        locale: str,
        user_message: str,
        recent_messages: list[ChatMessage],
        existing_context: OccasionContext | None,
    ) -> OccasionContext:
        context = existing_context.model_copy(deep=True) if existing_context is not None else OccasionContext()
        try:
            result = await self.vllm_client.extract_occasion_slots(
                locale=locale,
                user_message=user_message,
                conversation_history=self._build_conversation_history(recent_messages),
                existing_slots={
                    "event_type": context.event_type,
                    "venue": context.location,
                    "dress_code": context.dress_code,
                    "time_of_day": context.time_of_day,
                    "season_or_weather": context.weather_context or context.season,
                    "desired_impression": context.desired_impression,
                },
            )
            context.event_type = result.event_type or context.event_type
            context.location = result.venue or context.location
            context.time_of_day = result.time_of_day or context.time_of_day
            if result.season_or_weather:
                context.season = self._first_keyword_match(result.season_or_weather.lower(), SEASON_KEYWORDS) or context.season
                context.weather_context = result.season_or_weather
            context.dress_code = result.dress_code or context.dress_code
            context.desired_impression = result.desired_impression or context.desired_impression
        except VLLMClientError as exc:
            logger.warning("vLLM occasion extraction is unavailable; using deterministic slot parsing: %s", exc)

        lowered = user_message.lower()
        context.event_type = context.event_type or self._first_keyword_match(lowered, EVENT_TYPE_KEYWORDS)
        context.location = context.location or self._first_keyword_match(lowered, LOCATION_KEYWORDS)
        context.time_of_day = context.time_of_day or self._first_keyword_match(lowered, TIME_OF_DAY_KEYWORDS)
        context.season = context.season or self._first_keyword_match(lowered, SEASON_KEYWORDS)
        context.dress_code = context.dress_code or self._first_keyword_match(lowered, DRESS_CODE_KEYWORDS)
        context.desired_impression = context.desired_impression or self._first_keyword_match(lowered, IMPRESSION_KEYWORDS)
        context.weather_context = context.weather_context or self._first_keyword_match(lowered, WEATHER_KEYWORDS)
        context.is_sufficient_for_generation = not bool(context.missing_core_slots())
        return context

    async def _pick_style_direction(
        self,
        *,
        session: AsyncSession,
        session_id: str,
        style_history: list[StyleDirectionContext],
    ) -> tuple[StyleDirectionContext, StyleDirection | None]:
        recent_style_keys = {item.style_id or item.style_name for item in style_history[-5:] if item.style_id or item.style_name}
        today = datetime.now(timezone.utc).date()
        candidates = await style_directions_repository.list_active_not_shown_today(session, session_id=session_id, shown_on=today)
        if not candidates:
            candidates = await style_directions_repository.list_active(session)
        for candidate in candidates:
            if candidate.slug not in recent_style_keys and candidate.title_en not in recent_style_keys:
                return self._style_context_from_model(candidate), candidate
        if candidates:
            return self._style_context_from_model(candidates[0]), candidates[0]
        fallback = FALLBACK_STYLE_LIBRARY[len(style_history) % len(FALLBACK_STYLE_LIBRARY)]
        return StyleDirectionContext.model_validate(fallback), None

    async def _record_style_exposure(self, session: AsyncSession, session_id: str, style_direction: StyleDirection) -> None:
        today = datetime.now(timezone.utc).date()
        existing = await stylist_style_exposures_repository.get_for_session_day_and_style(
            session,
            session_id=session_id,
            style_direction_id=style_direction.id,
            shown_on=today,
        )
        if existing is None:
            await stylist_style_exposures_repository.create(
                session,
                {
                    "session_id": session_id,
                    "style_direction_id": style_direction.id,
                    "shown_on": today,
                },
            )

    def _style_context_from_model(self, style_direction: StyleDirection) -> StyleDirectionContext:
        descriptor_parts = [item.strip() for item in style_direction.descriptor_en.split(",") if item.strip()]
        return StyleDirectionContext(
            style_id=style_direction.slug,
            style_name=style_direction.title_en,
            palette=descriptor_parts[:3],
            silhouette=descriptor_parts[0] if descriptor_parts else None,
            hero_garments=descriptor_parts[1:3],
            styling_mood=descriptor_parts[-1] if descriptor_parts else None,
            composition_type="editorial flat lay",
            background_family="studio",
        )

    def _style_seed_from_context(self, style: StyleDirectionContext) -> dict[str, str]:
        descriptor_bits = [bit for bit in [style.silhouette, style.styling_mood, *style.hero_garments[:2]] if bit]
        descriptor = ", ".join(descriptor_bits) or style.style_name or "cohesive style direction"
        return {
            "slug": style.style_id or (style.style_name or "style-direction").lower().replace(" ", "-"),
            "title": style.style_name or "Style Direction",
            "descriptor": descriptor,
            "en": style.style_name or "Style Direction",
            "ru": style.style_name or "Style Direction",
        }

    def _style_history_to_prompt(self, style_history: list[StyleDirectionContext]) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for style in style_history[-5:]:
            title = style.style_name or "Style Direction"
            slug = style.style_id or title.lower().replace(" ", "-")
            items.append({"slug": slug, "title": title, "en": title, "ru": title})
        return items

    def _build_generation_prompt(
        self,
        *,
        user_message: str,
        image_brief_en: str,
        asset: UploadedAsset | None,
        profile_context: dict[str, str | int | None],
        style_seed: dict[str, str] | None,
        occasion_context: OccasionContext | None,
    ) -> str:
        compact_brief = re.sub(r"\s+", " ", image_brief_en).strip() or "cohesive editorial outfit"
        compact_brief = " ".join(compact_brief.split()[:24])
        asset_part = ""
        if asset is not None:
            asset_name = re.sub(r"\s+", " ", asset.original_filename).strip().rsplit(".", 1)[0][:48]
            asset_part = f" Anchor around the uploaded item {asset_name}. "
        body_part = ""
        height_cm = self._coerce_int(profile_context.get("height_cm"))
        weight_kg = self._coerce_int(profile_context.get("weight_kg"))
        if height_cm or weight_kg:
            body_part = f" Proportion hint only: {height_cm or 'n/a'} cm, {weight_kg or 'n/a'} kg. "
        gender = self._optional_text(profile_context.get("gender"))
        gender_part = ""
        if gender == "male":
            gender_part = " Menswear proportions only; no womenswear garments or feminine-coded accessories. "
        elif gender == "female":
            gender_part = " Womenswear proportions only; no menswear-only tailoring cues or masculine-coded accessories. "
        style_part = f" Style direction: {style_seed['title']}; {style_seed['descriptor']}. " if style_seed is not None else ""
        occasion_part = ""
        if occasion_context is not None:
            slots = [occasion_context.event_type, occasion_context.time_of_day, occasion_context.season, occasion_context.dress_code or occasion_context.desired_impression]
            compact_slots = [slot for slot in slots if slot]
            if compact_slots:
                occasion_part = f" Occasion context: {'; '.join(compact_slots[:4])}. "
        request_part = re.sub(r"\s+", " ", user_message).strip()
        request_text = f" User context: {' '.join(request_part.split()[:12])}. " if request_part else ""
        prompt = (
            "Luxury editorial flat lay, overhead, garments only; no model, mannequin, body parts, text, logos, collage, props, hanger, or watermark. "
            "One complete outfit only, 4 to 6 items max, fully visible, coherent, and readable. "
            "No duplicate categories, broken tailoring, clutter, or floating extras. "
            f"Brief: {compact_brief}. "
            f"{request_text}{occasion_part}{asset_part}{body_part}{gender_part}{style_part}"
        ).strip()
        return " ".join(prompt.split()[:95])

    def _build_context_patch(self, context: ChatModeContext) -> dict[str, Any]:
        patch: dict[str, Any] = {
            "active_mode": context.active_mode.value,
            "flow_state": context.flow_state.value,
            "last_decision_type": context.last_decision_type,
            "should_auto_generate": context.should_auto_generate,
            "current_job_id": context.current_job_id,
        }
        if context.clarification_kind is not None:
            patch["clarification_kind"] = context.clarification_kind.value
        if context.pending_clarification:
            patch["pending_clarification"] = context.pending_clarification
        if context.anchor_garment is not None:
            patch["anchor_garment"] = context.anchor_garment.model_dump(mode="json", exclude_none=True)
        if context.occasion_context is not None:
            patch["occasion_context"] = context.occasion_context.model_dump(mode="json", exclude_none=True)
        if context.current_style_name:
            patch["current_style_name"] = context.current_style_name
        return patch

    def _build_conversation_history(self, messages: list[ChatMessage], limit: int = 6) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for message in messages[-limit:]:
            if not message.content:
                continue
            role = "assistant"
            if message.role.value == "user":
                role = "user"
            elif message.role.value == "system":
                role = "system"
            history.append({"role": role, "content": message.content.strip()[:280]})
        return history

    def _explicitly_requests_generation(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in GENERATION_HINTS)

    def _infer_formality(self, lowered_text: str) -> str | None:
        if "formal" in lowered_text or "класс" in lowered_text or "вечер" in lowered_text:
            return "formal"
        if "smart casual" in lowered_text or "смарт" in lowered_text:
            return "smart-casual"
        if "casual" in lowered_text or "кэжуал" in lowered_text:
            return "casual"
        return None

    def _first_keyword_match(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                return canonical
        return None

    def _all_keyword_matches(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
        matches: list[str] = []
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                matches.append(canonical)
        return matches

    def _recoverable_error_text(self, locale: str) -> str:
        return (
            "Диалог получился слишком длинным для текущего шага. Попробуй переформулировать запрос короче или начни новый сценарий."
            if locale == "ru"
            else "This conversation became too long for the current step. Try a shorter request or start a new flow."
        )

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
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None


stylist_orchestrator = StylistChatOrchestrator()
