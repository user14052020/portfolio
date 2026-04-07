import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.vllm import VLLMClient, VLLMClientError, VLLMContextLimitError
from app.models import StyleDirection, StylistSessionState, UploadedAsset
from app.models.chat_message import ChatMessage
from app.models.enums import ChatMessageRole, GenerationStatus
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.style_directions import style_directions_repository
from app.repositories.stylist_session_states import stylist_session_states_repository
from app.repositories.stylist_style_exposures import stylist_style_exposures_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate
from app.schemas.stylist import StylistMessageRequest
from app.services.generation import generation_service

logger = logging.getLogger(__name__)

StylistRoute = Literal["text_only", "text_and_generation", "text_and_catalog"]
SessionIntent = Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"]

GENERATION_HINTS = (
    "generate",
    "render",
    "visualize",
    "visualise",
    "lookbook",
    "flat-lay",
    "flat lay",
    "сгенер",
    "визуал",
    "покажи пример",
    "пример образа",
)

STYLE_DIRECTIONS: tuple[dict[str, str], ...] = (
    {
        "slug": "artful_minimalism",
        "ru": "арт-минимализм",
        "en": "artful minimalism",
        "descriptor": "clean lines, sculptural layers, quiet palette, one thoughtful accent",
        "history_ru": "Это направление выросло из модернистского дизайна и привычки убирать лишнее, оставляя только форму, фактуру и ритм.",
        "history_en": "This direction grew out of modernist design and the habit of removing excess, leaving only form, texture, and rhythm.",
        "why_ru": "Оно хорошо работает, когда хочется выглядеть собранно и современно без тяжеловесной строгости.",
        "why_en": "It works well when you want to look composed and modern without feeling overly rigid.",
        "signature_items_en": "clean coat, precise knitwear, straight trousers, sharp shoes, restrained accessories",
    },
    {
        "slug": "soft_retro_prep",
        "ru": "мягкий ретро-prep",
        "en": "soft retro prep",
        "descriptor": "smart layers, collegiate textures, softened vintage mood, polished but relaxed",
        "history_ru": "У этого стиля корни в университетском гардеробе середины XX века: твид, трикотаж, рубашки и спокойная собранность без пафоса.",
        "history_en": "This style has roots in mid-20th-century collegiate wardrobes: tweed, knitwear, shirting, and an easy sense of polish.",
        "why_ru": "Он уместен, когда нужен живой и интеллигентный образ с характером, но без театральности.",
        "why_en": "It fits when you want an intelligent, characterful look without tipping into costume.",
        "signature_items_en": "oxford shirt, textured knit, relaxed blazer, pleated trousers, loafers or clean leather shoes",
    },
    {
        "slug": "relaxed_workwear",
        "ru": "расслабленный workwear",
        "en": "relaxed workwear",
        "descriptor": "practical layers, sturdy fabrics, clean utility details, grounded palette",
        "history_ru": "Этот язык одежды пришёл из рабочей формы и военного утилитарного гардероба, но со временем превратился в спокойную городскую классику.",
        "history_en": "This clothing language comes from work uniforms and military utility pieces, but over time became a calm urban classic.",
        "why_ru": "Он хорош, когда хочется внятной структуры, практичности и ощущения надёжности без формального дресс-кода.",
        "why_en": "It fits when you want structure, practicality, and a sense of reliability without a formal dress code.",
        "signature_items_en": "overshirt, chore jacket, sturdy trousers, substantial shoes, muted earthy palette",
    },
    {
        "slug": "scandi_soft",
        "ru": "мягкий скандинавский минимализм",
        "en": "soft Scandinavian minimalism",
        "descriptor": "airy silhouettes, tactile knitwear, light neutrals, calm proportions",
        "history_ru": "Скандинавский минимализм вырос из северной любви к свету, воздуху и тихой функциональности, где простота работает на ощущение качества.",
        "history_en": "Scandinavian minimalism grew from a northern love of light, air, and quiet functionality, where simplicity creates a sense of quality.",
        "why_ru": "Он особенно хорош, если нужен свежий, спокойный и визуально дорогой образ без жёсткой демонстративности.",
        "why_en": "It is especially strong when you want a fresh, calm, visually expensive look without overt display.",
        "signature_items_en": "soft coat, fluid trousers, tactile knit, light leather footwear, pale neutral palette",
    },
    {
        "slug": "urban_sport_chic",
        "ru": "городской sporty chic",
        "en": "urban sporty chic",
        "descriptor": "clean sporty lines, sharp layering, restrained color blocking, elevated casual energy",
        "history_ru": "Этот стиль вырос из встречи спортивной одежды и городского люкса, когда комфортные формы начали сочетать с более точным кроем и чистой отделкой.",
        "history_en": "This style grew from the meeting point between sportswear and urban luxury, when comfortable shapes were paired with cleaner tailoring and finish.",
        "why_ru": "Он подходит, когда хочется динамики и свободы, но при этом сохранить ощущение собранности и продуманности.",
        "why_en": "It suits moments when you want movement and ease while still looking deliberate and composed.",
        "signature_items_en": "sleek bomber or track-inspired layer, clean knit or tee, tapered trousers, sharp sneakers",
    },
)

SESSION_STATE_STATUS_AWAITING_PROFILE = "awaiting_profile"
SESSION_STATE_STATUS_AWAITING_GARMENT_DESCRIPTION = "awaiting_garment_description"
SESSION_STATE_STATUS_COLLECTING_OCCASION = "collecting_occasion"
SESSION_STATE_STATUS_READY = "ready"
OCCASION_SLOT_FIELDS = (
    "event_type",
    "venue",
    "dress_code",
    "time_of_day",
    "season_or_weather",
    "desired_impression",
)


@dataclass
class StylistDecision:
    reply_ru: str
    reply_en: str
    image_brief_en: str
    generation_prompt_en: str
    route: StylistRoute
    provider: str
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StylistService:
    def __init__(self) -> None:
        self.vllm_client = VLLMClient()

    async def process_message(self, session: AsyncSession, payload: StylistMessageRequest):
        locale = "ru" if payload.locale == "ru" else "en"
        await self._enforce_message_cooldown(session, payload.session_id, locale)
        recent_messages = await chat_messages_repository.list_by_session(session, payload.session_id, limit=20)
        latest_message = recent_messages[-1] if recent_messages else None
        session_state = await stylist_session_states_repository.get_by_session_id(session, payload.session_id)
        state_payload = self._normalize_session_state_payload(session_state.state_payload if session_state else None)

        asset = await self._resolve_context_asset(session, payload, recent_messages, latest_message)
        normalized_gender = self._normalize_gender(payload.profile_gender)
        requested_auto_generate = bool(payload.auto_generate)
        user_message_text = self._resolve_user_message_text(locale=locale, message=payload.message, asset=asset)
        routing_decision = await self._resolve_request_routing(
            locale=locale,
            user_message=user_message_text,
            asset=asset,
            latest_message=latest_message,
            recent_messages=recent_messages,
            requested_intent=payload.requested_intent,
            session_state=session_state,
            state_payload=state_payload,
        )
        session_intent = routing_decision["session_intent"]
        requires_occasion_clarification = routing_decision["requires_occasion_clarification"]
        effective_auto_generate = requested_auto_generate
        if session_intent == "general_advice" and not self._explicitly_requests_generation(user_message_text):
            effective_auto_generate = False

        await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.USER,
                "locale": locale,
                "content": user_message_text,
                "uploaded_asset_id": payload.uploaded_asset_id,
                "payload": {
                    "profile_gender": normalized_gender,
                    "body_height_cm": payload.body_height_cm,
                    "body_weight_kg": payload.body_weight_kg,
                    "session_intent": session_intent,
                    "context_asset_id": asset.id if asset else None,
                    "context_asset_name": asset.original_filename if asset else None,
                    "requested_intent": payload.requested_intent,
                    "auto_generate": effective_auto_generate,
                    "session_state_active_intent": session_intent,
                },
            },
        )

        conversation_messages = await chat_messages_repository.list_by_session(session, payload.session_id, limit=20)
        profile_context = self._collect_profile_context(
            messages=conversation_messages,
            explicit_gender=normalized_gender,
            explicit_height_cm=payload.body_height_cm,
            explicit_weight_kg=payload.body_weight_kg,
        )
        resolved_height_cm = self._coerce_int(profile_context.get("height_cm"))
        resolved_weight_kg = self._coerce_int(profile_context.get("weight_kg"))
        missing_profile_fields = self._get_missing_profile_fields(profile_context)
        style_direction = await self._resolve_style_direction(
            session=session,
            session_id=payload.session_id,
            session_intent=session_intent,
            state_payload=state_payload,
            explicit_refresh=payload.requested_intent == "style_exploration",
        )
        style_seed = self._style_direction_to_seed(style_direction)
        previous_style_directions = await self._collect_previous_style_directions_from_catalog(
            session,
            payload.session_id,
            exclude_slug=style_seed["slug"] if style_seed is not None else None,
        )
        occasion_context = await self._resolve_occasion_context(
            locale=locale,
            user_message=user_message_text,
            conversation_messages=conversation_messages,
            state_payload=state_payload,
            session_intent=session_intent,
        )
        if session_intent == "occasion_outfit":
            requires_occasion_clarification = requires_occasion_clarification or self._occasion_slots_missing_core(
                occasion_context
            )

        garment_context = await self._resolve_garment_context(
            user_message=user_message_text,
            conversation_messages=conversation_messages,
            session_intent=session_intent,
            asset=asset,
        )
        needs_garment_description = (
            session_intent == "garment_matching"
            and asset is None
            and not garment_context.get("has_specific_garment")
        )

        if session_intent == "style_exploration" and style_direction is not None:
            await self._record_style_exposure(session, payload.session_id, style_direction)

        if needs_garment_description:
            decision = self._build_garment_description_request_decision(locale=locale)
            effective_auto_generate = False
        elif requires_occasion_clarification:
            decision = self._build_occasion_clarification_decision(
                locale=locale,
                pending_generation=effective_auto_generate,
                occasion_context=occasion_context,
            )
        elif self._requires_profile(session_intent) and missing_profile_fields:
            decision = self._build_profile_clarification_decision(
                locale=locale,
                missing_fields=missing_profile_fields,
                profile_context=profile_context,
                pending_intent=session_intent,
                style_seed=style_seed,
            )
        else:
            decision = await self._make_stylist_decision(
                locale=locale,
                user_message=user_message_text,
                asset=asset,
                body_height_cm=resolved_height_cm,
                body_weight_kg=resolved_weight_kg,
                auto_generate=effective_auto_generate,
                conversation_history=self._build_conversation_history(conversation_messages),
                profile_context=profile_context,
                session_intent=session_intent,
                style_seed=style_seed,
                previous_style_directions=previous_style_directions,
                occasion_context=occasion_context or None,
            )

        generation_job = None
        if self._should_create_generation_job(auto_generate=effective_auto_generate, route=decision.route):
            existing_generation_job = await generation_jobs_repository.get_latest_active_by_session(
                session,
                payload.session_id,
            )
            if existing_generation_job is not None and self._is_generation_job_active(existing_generation_job.status):
                generation_job = await generation_service.enrich_job_runtime(session, existing_generation_job)
                decision = self._build_existing_generation_job_decision(
                    locale=locale,
                    existing_job=generation_job,
                    fallback_decision=decision,
                )
            else:
                generation_job = await generation_service.create_and_submit(
                    session,
                    GenerationJobCreate(
                        session_id=payload.session_id,
                        input_text=user_message_text,
                        recommendation_ru=decision.reply_ru,
                        recommendation_en=decision.reply_en,
                        prompt=decision.generation_prompt_en,
                        input_asset_id=asset.id if asset else None,
                        body_height_cm=resolved_height_cm,
                        body_weight_kg=resolved_weight_kg,
                    ),
                )

        response_text = decision.reply_ru if locale == "ru" else decision.reply_en
        defer_reply_until_image_ready = (
            generation_job is not None
            and session_intent == "style_exploration"
        )
        assistant_payload = {
            "prompt": decision.generation_prompt_en,
            "image_brief_en": decision.image_brief_en,
            "route": decision.route,
            "provider": decision.provider,
            "model": decision.model,
            "defer_reply_until_image_ready": defer_reply_until_image_ready,
            **decision.metadata,
        }
        if occasion_context:
            assistant_payload["occasion_context"] = occasion_context
        assistant_message = await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.ASSISTANT,
                "locale": locale,
                "content": response_text,
                "generation_job_id": generation_job.id if generation_job else None,
                "payload": assistant_payload,
            },
        )
        assistant_message = await chat_messages_repository.get_with_relations(session, assistant_message.id)
        if assistant_message is None:
            raise RuntimeError("Assistant message was not found after creation")
        if assistant_message.generation_job is not None:
            assistant_message.generation_job = await generation_service.enrich_job_runtime(
                session,
                assistant_message.generation_job,
            )

        next_state_payload = self._build_next_session_state_payload(
            current_state=state_payload,
            session_intent=session_intent,
            decision=decision,
            style_seed=style_seed,
            garment_context=garment_context,
            occasion_context=occasion_context,
        )
        await self._upsert_session_state(
            session=session,
            session_id=payload.session_id,
            session_state=session_state,
            active_intent=session_intent if next_state_payload else None,
            state_payload=next_state_payload,
        )
        await chat_messages_repository.trim_session(session, payload.session_id, keep_latest=50)

        return {
            "session_id": payload.session_id,
            "recommendation_text": response_text,
            "recommendation_text_ru": decision.reply_ru,
            "recommendation_text_en": decision.reply_en,
            "prompt": decision.generation_prompt_en,
            "assistant_message": assistant_message,
            "generation_job": generation_job,
            "timestamp": datetime.now(UTC),
        }

    async def get_history(self, session: AsyncSession, session_id: str):
        history = await chat_messages_repository.list_by_session(session, session_id, limit=50)
        for message in history:
            if message.generation_job is not None:
                message.generation_job = await generation_service.enrich_job_runtime(session, message.generation_job)
        return history

    async def get_history_page(
        self,
        session: AsyncSession,
        session_id: str,
        *,
        limit: int = 5,
        before_message_id: int | None = None,
    ) -> dict[str, Any]:
        items, has_more = await chat_messages_repository.list_page_by_session(
            session,
            session_id,
            limit=limit,
            before_message_id=before_message_id,
        )
        for message in items:
            if message.generation_job is not None:
                message.generation_job = await generation_service.enrich_job_runtime(session, message.generation_job)

        next_before_message_id = items[0].id if items and has_more else None
        return {
            "items": items,
            "has_more": has_more,
            "next_before_message_id": next_before_message_id,
        }

    async def _enforce_message_cooldown(self, session: AsyncSession, session_id: str, locale: str) -> None:
        latest_assistant_message = await chat_messages_repository.get_latest_assistant_message(session, session_id)
        if latest_assistant_message is None:
            return

        cooldown_seconds = max(generation_service.settings.chat_message_cooldown_seconds, 0)
        if cooldown_seconds <= 0:
            return

        next_allowed_at = latest_assistant_message.created_at + timedelta(seconds=cooldown_seconds)
        remaining_seconds = int((next_allowed_at - datetime.now(UTC)).total_seconds())
        if remaining_seconds <= 0:
            return

        raise self._build_message_cooldown_error(
            locale=locale,
            retry_after_seconds=remaining_seconds,
            next_allowed_at=next_allowed_at,
        )

    def _build_llm_unavailable_error(self, locale: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Чат временно офлайн: языковая модель недоступна. Попробуйте отправить сообщение позже."
                if locale == "ru"
                else "The chat is temporarily offline because the language model is unavailable. Please try again later."
            ),
        )

    def _build_message_cooldown_error(
        self,
        *,
        locale: str,
        retry_after_seconds: int,
        next_allowed_at: datetime,
    ) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "message_cooldown",
                "message": (
                    "Отправлять новые сообщения можно не чаще одного раза в минуту. Подождите немного и попробуйте снова."
                    if locale == "ru"
                    else "Messages can only be sent once per minute. Please wait a moment and try again."
                ),
                "retry_after_seconds": retry_after_seconds,
                "next_allowed_at": next_allowed_at.isoformat(),
            },
        )

    def _build_context_limit_error(self, locale: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Диалог получился слишком длинным для текущей языковой модели. Попробуйте отправить более короткий запрос или начать новый чат."
                if locale == "ru"
                else "This conversation has grown too long for the current language model. Try a shorter request or start a new chat."
            ),
        )

    async def _resolve_request_routing(
        self,
        *,
        locale: str,
        user_message: str,
        asset: UploadedAsset | None,
        latest_message: ChatMessage | None,
        recent_messages: list[ChatMessage],
        requested_intent: SessionIntent | None,
        session_state: StylistSessionState | None,
        state_payload: dict[str, Any],
    ) -> dict[str, Any]:
        if requested_intent in {"garment_matching", "style_exploration", "occasion_outfit"}:
            return {
                "session_intent": requested_intent,
                "requires_occasion_clarification": requested_intent == "occasion_outfit",
            }

        active_state_intent = self._extract_active_state_intent(session_state, state_payload)
        if active_state_intent == "garment_matching" and (
            self._state_requires_garment_follow_up(state_payload) or self._state_requires_profile_follow_up(state_payload)
        ):
            return {
                "session_intent": "garment_matching",
                "requires_occasion_clarification": False,
            }
        if active_state_intent == "style_exploration" and self._state_requires_profile_follow_up(state_payload):
            return {
                "session_intent": "style_exploration",
                "requires_occasion_clarification": False,
            }
        if active_state_intent == "occasion_outfit" and self._state_requires_occasion_follow_up(state_payload):
            return {
                "session_intent": "occasion_outfit",
                "requires_occasion_clarification": False,
            }

        latest_assistant_payload: dict[str, Any] | None = None
        if latest_message is not None and latest_message.role == ChatMessageRole.ASSISTANT:
            latest_assistant_payload = latest_message.payload if isinstance(latest_message.payload, dict) else {}

        try:
            routing = await self.vllm_client.classify_stylist_intent(
                user_message=user_message,
                uploaded_asset_name=asset.original_filename if asset else None,
                conversation_history=self._build_conversation_history(recent_messages),
                latest_assistant_payload=latest_assistant_payload,
                session_state=self._build_routing_state_payload(session_state, state_payload),
            )
            return {
                "session_intent": routing.session_intent,
                "requires_occasion_clarification": routing.requires_occasion_clarification,
            }
        except VLLMClientError as exc:
            logger.warning("vLLM routing is unavailable; using structured fallback routing: %s", exc)
            return self._resolve_structured_routing_fallback(asset=asset, latest_message=latest_message)

    async def _make_stylist_decision(
        self,
        *,
        locale: str,
        user_message: str,
        asset: UploadedAsset | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        conversation_history: list[dict[str, str]],
        profile_context: dict[str, str | int | None],
        session_intent: SessionIntent,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, str]],
        occasion_context: dict[str, str] | None,
    ) -> StylistDecision:
        try:
            result = await self.vllm_client.generate_stylist_response(
                locale=locale,
                user_message=user_message,
                uploaded_asset_name=asset.original_filename if asset else None,
                body_height_cm=body_height_cm,
                body_weight_kg=body_weight_kg,
                auto_generate=auto_generate,
                conversation_history=conversation_history,
                profile_context=profile_context,
                session_intent=session_intent,
                style_seed=style_seed,
                previous_style_directions=previous_style_directions,
                occasion_context=occasion_context,
            )
            image_brief_en = result.image_brief_en.strip() or result.reply_en
            return StylistDecision(
                reply_ru=result.reply_ru,
                reply_en=result.reply_en,
                image_brief_en=image_brief_en,
                generation_prompt_en=self._build_generation_prompt(
                    user_message=user_message,
                    image_brief_en=image_brief_en,
                    asset=asset,
                    body_height_cm=body_height_cm,
                    body_weight_kg=body_weight_kg,
                    profile_context=profile_context,
                    session_intent=session_intent,
                    style_seed=style_seed,
                    occasion_context=occasion_context,
                ),
                route=self._resolve_route(
                    requested_route=result.route,
                    auto_generate=auto_generate,
                    session_intent=session_intent,
                ),
                provider="vllm",
                model=result.model,
                metadata={
                    "session_intent": session_intent,
                    "style_seed": style_seed,
                    "profile_context": profile_context,
                    "asset_name": asset.original_filename if asset else None,
                    "occasion_context": occasion_context,
                },
            )
        except VLLMContextLimitError as exc:
            logger.warning("vLLM generation hit context limit: %s", exc)
            raise self._build_context_limit_error(locale)
        except VLLMClientError as exc:
            logger.warning("vLLM generation is unavailable; using structured fallback decision: %s", exc)
            return self._build_fallback_decision(
                locale=locale,
                user_message=user_message,
                asset=asset,
                body_height_cm=body_height_cm,
                body_weight_kg=body_weight_kg,
                auto_generate=auto_generate,
                profile_context=profile_context,
                session_intent=session_intent,
                style_seed=style_seed,
                occasion_context=occasion_context,
            )

    def _build_fallback_decision(
        self,
        *,
        locale: str,
        user_message: str,
        asset: UploadedAsset | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        profile_context: dict[str, str | int | None],
        session_intent: SessionIntent,
        style_seed: dict[str, str] | None,
        occasion_context: dict[str, str] | None,
    ) -> StylistDecision:
        compact_asset_name = ""
        if asset is not None:
            compact_asset_name = re.sub(r"\s+", " ", asset.original_filename).strip()
            compact_asset_name = compact_asset_name.rsplit(".", 1)[0].strip(" -_.")[:48]

        if session_intent == "style_exploration" and style_seed is not None:
            reply_ru = (
                f"Соберу новый образ в направлении «{style_seed['ru']}». "
                "Сохраню цельный силуэт, чистую логику слоев и спокойный набор вещей, "
                "чтобы образ читался современно и без перегруза."
            )
            reply_en = (
                f"I will build a new outfit in the {style_seed['en']} direction. "
                "I will keep the silhouette cohesive, the layering clean, and the item set restrained "
                "so the result feels modern and controlled."
            )
            image_brief_en = (
                f"{style_seed['en']}; {style_seed['descriptor']}; "
                "one cohesive editorial flat lay outfit with clear wardrobe logic"
            )
        elif session_intent == "garment_matching":
            reply_ru = (
                f"Соберу комплект вокруг вещи «{compact_asset_name}». "
                if compact_asset_name
                else "Соберу комплект вокруг вашей вещи. "
            )
            reply_ru += (
                "Оставлю один цельный образ, без дублей и лишних аксессуаров, "
                "чтобы главный предмет читался ясно и не терялся."
            )
            reply_en = (
                f"I will build the outfit around {compact_asset_name}. "
                if compact_asset_name
                else "I will build the outfit around your garment. "
            )
            reply_en += (
                "I will keep it to one coherent look, without duplicates or noisy accessories, "
                "so the anchor item stays clear and readable."
            )
            image_brief_en = (
                f"one coherent outfit built around {compact_asset_name}; "
                if compact_asset_name
                else "one coherent outfit built around the uploaded garment; "
            )
            image_brief_en += (
                "clean flat lay, clear anchor item, restrained styling, no duplicate categories"
            )
        elif session_intent == "occasion_outfit":
            event_hint = occasion_context.get("event_type") if occasion_context else None
            reply_ru = (
                "Соберу уместный образ под мероприятие и сохраню спокойную, собранную стилистику "
                "без перегруза деталями."
            )
            reply_en = (
                "I will build an event-appropriate outfit and keep the styling composed, polished, "
                "and free from unnecessary detail."
            )
            image_brief_en = (
                "event-appropriate polished outfit, one coherent flat lay, clean styling, no clutter"
            )
            reply_ru = (
                f"Соберу уместный образ для {event_hint}. " if event_hint else "Соберу уместный образ под мероприятие. "
            ) + "Сохраню спокойную, собранную стилистику без перегруза деталями."
            reply_en = (
                f"I will build an outfit for {event_hint}. "
                if event_hint
                else "I will build an event-appropriate outfit. "
            ) + "I will keep the styling composed, polished, and free from unnecessary detail."
            image_brief_en = (
                f"outfit for {event_hint}, polished and context-aware, one coherent flat lay, clean styling, no clutter"
                if event_hint
                else "event-appropriate polished outfit, one coherent flat lay, clean styling, no clutter"
            )
        else:
            reply_ru = (
                "Сейчас дам практичную стилистическую рекомендацию и сохраню образ цельным, "
                "современным и носибельным."
            )
            reply_en = (
                "I will keep the recommendation practical and make the outfit feel cohesive, "
                "modern, and wearable."
            )
            image_brief_en = (
                "cohesive modern outfit, wearable wardrobe logic, clean editorial flat lay"
            )

        requested_route: StylistRoute = "text_and_generation" if auto_generate else "text_only"
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en=image_brief_en,
            generation_prompt_en=self._build_generation_prompt(
                user_message=user_message,
                image_brief_en=image_brief_en,
                asset=asset,
                body_height_cm=body_height_cm,
                body_weight_kg=body_weight_kg,
                profile_context=profile_context,
                session_intent=session_intent,
                style_seed=style_seed,
                occasion_context=occasion_context,
            ),
            route=self._resolve_route(
                requested_route=requested_route,
                auto_generate=auto_generate,
                session_intent=session_intent,
            ),
            provider="fallback",
            metadata={
                "session_intent": session_intent,
                "style_seed": style_seed,
                "profile_context": profile_context,
                "asset_name": asset.original_filename if asset else None,
                "occasion_context": occasion_context,
                "fallback_reason": "vllm_unavailable",
                "fallback_locale": locale,
            },
        )

    def _build_garment_description_request_decision(self, *, locale: str) -> StylistDecision:
        reply_ru = (
            "Пришлите фото вещи, вокруг которой нужно собрать комплект. "
            "Если по фото предмет может читаться неочевидно, можно коротко подписать, что это за вещь."
        )
        reply_ru = (
            "Опишите вещь, вокруг которой нужно собрать образ: что это за предмет, какого он цвета, из какого материала и как сидит. "
            "Достаточно одной короткой строки, например: темно-синяя джинсовая рубашка прямого кроя."
        )
        reply_en = (
            "Describe the garment you want to build the outfit around: what it is, the color, the material, and the fit. "
            "One short line is enough, for example: a dark-blue straight-fit denim shirt."
        )
        known_bits: list[str] = []
        if occasion_context.get("venue"):
            known_bits.append(
                f"площадка: {occasion_context['venue']}" if locale == "ru" else f"venue: {occasion_context['venue']}"
            )
        if occasion_context.get("dress_code"):
            known_bits.append(
                f"дресс-код: {occasion_context['dress_code']}"
                if locale == "ru"
                else f"dress code: {occasion_context['dress_code']}"
            )
        context_suffix = ""
        if known_bits:
            context_suffix = (
                f" Уже вижу: {', '.join(known_bits)}."
                if locale == "ru"
                else f" I already have: {', '.join(known_bits)}."
            )
        reply_ru = (
            "С радостью помогу. Сначала уточните, пожалуйста, что это за мероприятие: свадьба, свидание, ужин, корпоратив, театр, вечеринка или что-то другое. "
            "Если знаете, можно сразу добавить время суток и дресс-код."
        ) + context_suffix
        reply_en = (
            "Happy to help. First, tell me what kind of event it is: a wedding, date, dinner, work event, theater night, party, or something else. "
            "If you know it, you can also add the time of day and dress code."
        ) + context_suffix
        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en="",
            generation_prompt_en="",
            route="text_only",
            provider="garment_gate",
            metadata={
                "kind": "garment_description_request",
                "pending_intent": "garment_matching",
                "pending_generation": True,
                "primary_reply": primary_reply,
            },
        )

    def _build_existing_generation_job_decision(
        self,
        *,
        locale: str,
        existing_job,
        fallback_decision: StylistDecision,
    ) -> StylistDecision:
        if existing_job.status == GenerationStatus.PENDING:
            reply_ru = (
                "У вас уже есть задача на генерацию изображения. Она поставлена в очередь. "
                "Новый запрос на картинку не запускаю, чтобы не создавать дубли."
            )
            reply_en = (
                "You already have an image generation task. It is currently waiting in the queue. "
                "I am not starting another image request to avoid duplicates."
            )
        else:
            reply_ru = (
                "У вас уже есть активная генерация изображения. Дождитесь её завершения; "
                "пока можно продолжать переписку текстом."
            )
            reply_en = (
                "You already have an active image generation task. Let it finish first; "
                "in the meantime we can continue chatting in text."
            )

        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en=fallback_decision.image_brief_en,
            generation_prompt_en=fallback_decision.generation_prompt_en,
            route="text_only",
            provider="generation_guard",
            model=fallback_decision.model,
            metadata={
                **fallback_decision.metadata,
                "existing_generation_job_public_id": existing_job.public_id,
            },
        )

    def _resolve_structured_routing_fallback(
        self,
        *,
        asset: UploadedAsset | None,
        latest_message: ChatMessage | None,
    ) -> dict[str, Any]:
        pending_intent = self._extract_pending_intent(latest_message)

        if asset is not None:
            return {
                "session_intent": "garment_matching",
                "requires_occasion_clarification": False,
            }

        if pending_intent in {"garment_matching", "style_exploration"}:
            return {
                "session_intent": pending_intent,
                "requires_occasion_clarification": False,
            }

        if pending_intent == "occasion_outfit":
            return {
                "session_intent": "occasion_outfit",
                "requires_occasion_clarification": True,
            }

        return {
            "session_intent": "general_advice",
            "requires_occasion_clarification": False,
        }

    def _build_occasion_clarification_decision(
        self,
        *,
        locale: str,
        pending_generation: bool,
        occasion_context: dict[str, str],
    ) -> StylistDecision:
        reply_ru = (
            "С радостью помогу. Сначала уточните, пожалуйста, что это за мероприятие: свадьба, свидание, ужин, корпоратив, театр, вечеринка или что-то другое. "
            "Если знаете, можно сразу добавить время суток и дресс-код."
        )
        reply_en = (
            "Happy to help. First, tell me what kind of event it is: a wedding, date, dinner, work event, theater night, party, or something else. "
            "If you know it, you can also add the time of day and dress code."
        )
        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en="",
            generation_prompt_en="",
            route="text_only",
            provider="occasion_gate",
            metadata={
                "kind": "occasion_clarification",
                "pending_intent": "occasion_outfit",
                "pending_generation": pending_generation,
                "primary_reply": primary_reply,
                "occasion_context": occasion_context,
            },
        )

    def _build_profile_clarification_decision(
        self,
        *,
        locale: str,
        missing_fields: tuple[str, ...],
        profile_context: dict[str, str | int | None],
        pending_intent: SessionIntent,
        style_seed: dict[str, str] | None,
    ) -> StylistDecision:
        missing_labels_ru = {"gender": "пол", "height_cm": "рост", "weight_kg": "вес"}
        missing_labels_en = {"gender": "gender", "height_cm": "height", "weight_kg": "weight"}
        missing_ru = ", ".join(missing_labels_ru[field] for field in missing_fields)
        missing_en = ", ".join(missing_labels_en[field] for field in missing_fields)

        if pending_intent == "style_exploration" and style_seed:
            reply_ru = (
                f"Прежде чем я соберу новый образ в направлении «{style_seed['ru']}», уточните, пожалуйста: {missing_ru}. "
                "Напишите это одним сообщением, например: мужчина, 182 см, 78 кг."
            )
            reply_en = (
                f"Before I build a new look in the {style_seed['en']} direction, please confirm your {missing_en}. "
                "Send it in one line, for example: male, 182 cm, 78 kg."
            )
        elif pending_intent == "garment_matching":
            reply_ru = (
                f"Чтобы я собрал комплект вокруг вашей вещи и нормально подогнал силуэт, уточните: {missing_ru}. "
                "Напишите это одним сообщением, например: мужчина, 182 см, 78 кг."
            )
            reply_en = (
                f"To build the outfit around your garment and tune the proportions properly, please confirm your {missing_en}. "
                "Send it in one line, for example: male, 182 cm, 78 kg."
            )
        else:
            reply_ru = (
                f"Прежде чем я соберу более точную рекомендацию, уточните: {missing_ru}. "
                "Напишите это одним сообщением, например: мужчина, 182 см, 78 кг."
            )
            reply_en = (
                f"Before I give a more precise recommendation, please confirm your {missing_en}. "
                "Send it in one line, for example: male, 182 cm, 78 kg."
            )

        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en="",
            generation_prompt_en="",
            route="text_only",
            provider="profile_gate",
            metadata={
                "kind": "profile_clarification",
                "missing_profile_fields": list(missing_fields),
                "profile_context": profile_context,
                "pending_intent": pending_intent,
                "pending_generation": pending_intent in {"garment_matching", "style_exploration"},
                "pending_style_seed": style_seed,
                "primary_reply": primary_reply,
            },
        )

    def _has_pending_generation(self, latest_message: ChatMessage | None) -> bool:
        if latest_message is None or latest_message.role != ChatMessageRole.ASSISTANT:
            return False
        payload = latest_message.payload if isinstance(latest_message.payload, dict) else {}
        return bool(payload.get("pending_generation"))

    def _is_generation_job_active(self, status: GenerationStatus) -> bool:
        return status in {GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING}

    async def _resolve_context_asset(
        self,
        session: AsyncSession,
        payload: StylistMessageRequest,
        recent_messages: list[ChatMessage],
        latest_message: ChatMessage | None,
    ) -> UploadedAsset | None:
        if payload.uploaded_asset_id:
            asset = await uploads_repository.get(session, payload.uploaded_asset_id)
            if asset is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded asset was not found.")
            return asset

        raw_message = (payload.message or "").strip().lower()
        should_reuse_history_asset = (
            not raw_message
            or self._extract_pending_intent(latest_message) == "garment_matching"
        )
        if not should_reuse_history_asset:
            return None

        for message in reversed(recent_messages):
            if message.role != ChatMessageRole.USER:
                continue
            if message.uploaded_asset is not None:
                return message.uploaded_asset

        return None

    def _resolve_user_message_text(
        self,
        *,
        locale: str,
        message: str | None,
        asset: UploadedAsset | None,
    ) -> str:
        trimmed = (message or "").strip()
        if trimmed:
            return trimmed
        if asset is not None:
            return f"Фото вещи: {asset.original_filename}" if locale == "ru" else f"Item photo: {asset.original_filename}"
        return "Нужна рекомендация по образу" if locale == "ru" else "Need outfit guidance"

    def _extract_pending_intent(self, latest_message: ChatMessage | None) -> SessionIntent | None:
        if latest_message is None or latest_message.role != ChatMessageRole.ASSISTANT:
            return None
        payload = latest_message.payload if isinstance(latest_message.payload, dict) else {}
        pending_intent = payload.get("pending_intent")
        if pending_intent in {"general_advice", "garment_matching", "style_exploration", "occasion_outfit"}:
            return pending_intent
        return None

    def _explicitly_requests_generation(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in GENERATION_HINTS)

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "n/a"}:
            return None
        return cleaned

    def _normalize_session_state_payload(self, state_payload: Any) -> dict[str, Any]:
        return dict(state_payload) if isinstance(state_payload, dict) else {}

    def _extract_active_state_intent(
        self,
        session_state: StylistSessionState | None,
        state_payload: dict[str, Any],
    ) -> SessionIntent | None:
        candidate = None
        if session_state is not None:
            candidate = session_state.active_intent
        if not candidate:
            candidate = state_payload.get("active_intent")
        if candidate in {"general_advice", "garment_matching", "style_exploration", "occasion_outfit"}:
            return candidate
        return None

    def _build_routing_state_payload(
        self,
        session_state: StylistSessionState | None,
        state_payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        active_intent = self._extract_active_state_intent(session_state, state_payload)
        if active_intent is None and not state_payload:
            return None
        return {
            "active_intent": active_intent,
            "status": self._optional_text(state_payload.get("status")),
            "style_slug": self._optional_text(state_payload.get("style_slug")),
            "garment_description": self._optional_text(state_payload.get("garment_description")),
            "occasion_context": self._extract_occasion_context_from_state(state_payload),
        }

    def _state_requires_profile_follow_up(self, state_payload: dict[str, Any]) -> bool:
        return self._optional_text(state_payload.get("status")) == SESSION_STATE_STATUS_AWAITING_PROFILE

    def _state_requires_garment_follow_up(self, state_payload: dict[str, Any]) -> bool:
        return self._optional_text(state_payload.get("status")) == SESSION_STATE_STATUS_AWAITING_GARMENT_DESCRIPTION

    def _state_requires_occasion_follow_up(self, state_payload: dict[str, Any]) -> bool:
        return self._optional_text(state_payload.get("status")) == SESSION_STATE_STATUS_COLLECTING_OCCASION

    def _extract_occasion_context_from_state(self, state_payload: dict[str, Any]) -> dict[str, str]:
        raw_context = state_payload.get("occasion_context")
        if not isinstance(raw_context, dict):
            return {}
        normalized: dict[str, str] = {}
        for field in OCCASION_SLOT_FIELDS:
            value = self._optional_text(raw_context.get(field))
            if value:
                normalized[field] = value
        return normalized

    async def _resolve_occasion_context(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_messages: list[ChatMessage],
        state_payload: dict[str, Any],
        session_intent: SessionIntent,
    ) -> dict[str, str]:
        existing_context = self._extract_occasion_context_from_state(state_payload)
        if session_intent != "occasion_outfit":
            return existing_context

        try:
            extracted = await self.vllm_client.extract_occasion_slots(
                locale=locale,
                user_message=user_message,
                conversation_history=self._build_conversation_history(conversation_messages),
                existing_slots=existing_context,
            )
        except VLLMClientError as exc:
            logger.warning("vLLM occasion slot extraction is unavailable; using stored occasion state: %s", exc)
            return existing_context

        merged = dict(existing_context)
        for field in OCCASION_SLOT_FIELDS:
            value = self._optional_text(getattr(extracted, field))
            if value:
                merged[field] = value
        return merged

    def _occasion_slots_missing_core(self, occasion_context: dict[str, str]) -> bool:
        return not bool(self._optional_text(occasion_context.get("event_type")))

    async def _resolve_garment_context(
        self,
        *,
        user_message: str,
        conversation_messages: list[ChatMessage],
        session_intent: SessionIntent,
        asset: UploadedAsset | None,
    ) -> dict[str, Any]:
        if session_intent != "garment_matching":
            return {"has_specific_garment": False, "garment_description": None}
        if asset is not None:
            garment_name = asset.original_filename.rsplit(".", 1)[0]
            return {"has_specific_garment": True, "garment_description": garment_name}

        try:
            garment_result = await self.vllm_client.analyze_garment_request(
                user_message=user_message,
                conversation_history=self._build_conversation_history(conversation_messages),
            )
            return {
                "has_specific_garment": garment_result.has_specific_garment,
                "garment_description": garment_result.garment_description,
            }
        except VLLMClientError as exc:
            logger.warning("vLLM garment analysis is unavailable; using lightweight fallback: %s", exc)
            has_description = len(user_message.split()) >= 4
            return {
                "has_specific_garment": has_description,
                "garment_description": user_message if has_description else None,
            }

    async def _resolve_style_direction(
        self,
        *,
        session: AsyncSession,
        session_id: str,
        session_intent: SessionIntent,
        state_payload: dict[str, Any],
        explicit_refresh: bool,
    ) -> StyleDirection | None:
        if session_intent != "style_exploration":
            return None

        if not explicit_refresh and self._state_requires_profile_follow_up(state_payload):
            style_slug = self._optional_text(state_payload.get("style_slug"))
            if style_slug:
                return await style_directions_repository.get_by_slug(session, style_slug)

        shown_on = datetime.now(UTC).date()
        return await style_directions_repository.pick_random_active_style(
            session,
            session_id=session_id,
            shown_on=shown_on,
        )

    def _style_direction_to_seed(self, style_direction: StyleDirection | None) -> dict[str, str] | None:
        if style_direction is None:
            return None
        return {
            "slug": style_direction.slug,
            "ru": style_direction.title_ru,
            "en": style_direction.title_en,
            "descriptor": style_direction.descriptor_en,
        }

    async def _record_style_exposure(
        self,
        session: AsyncSession,
        session_id: str,
        style_direction: StyleDirection,
    ) -> None:
        shown_on = datetime.now(UTC).date()
        existing = await stylist_style_exposures_repository.get_for_session_day_and_style(
            session,
            session_id=session_id,
            style_direction_id=style_direction.id,
            shown_on=shown_on,
        )
        if existing is None:
            await stylist_style_exposures_repository.create(
                session,
                {
                    "session_id": session_id,
                    "style_direction_id": style_direction.id,
                    "shown_on": shown_on,
                },
            )

    async def _collect_previous_style_directions_from_catalog(
        self,
        session: AsyncSession,
        session_id: str,
        *,
        exclude_slug: str | None = None,
    ) -> list[dict[str, str]]:
        shown_on = datetime.now(UTC).date()
        exposures = await stylist_style_exposures_repository.list_for_session_day(
            session,
            session_id=session_id,
            shown_on=shown_on,
        )
        active_styles = await style_directions_repository.list_active(session)
        styles_by_id = {style.id: style for style in active_styles}
        directions: list[dict[str, str]] = []
        seen_slugs: set[str] = set()
        for exposure in exposures:
            style = styles_by_id.get(exposure.style_direction_id)
            if style is None or style.slug == exclude_slug or style.slug in seen_slugs:
                continue
            seen_slugs.add(style.slug)
            directions.append({"slug": style.slug, "ru": style.title_ru, "en": style.title_en})
        return directions

    def _build_next_session_state_payload(
        self,
        *,
        current_state: dict[str, Any],
        session_intent: SessionIntent,
        decision: StylistDecision,
        style_seed: dict[str, str] | None,
        garment_context: dict[str, Any],
        occasion_context: dict[str, str],
    ) -> dict[str, Any]:
        metadata = decision.metadata if isinstance(decision.metadata, dict) else {}
        kind = self._optional_text(metadata.get("kind"))

        if session_intent == "style_exploration":
            return {
                "status": SESSION_STATE_STATUS_AWAITING_PROFILE if kind == "profile_clarification" else SESSION_STATE_STATUS_READY,
                "style_slug": style_seed["slug"] if style_seed else None,
            }

        if session_intent == "garment_matching":
            next_state = {
                "status": SESSION_STATE_STATUS_READY,
                "garment_description": self._optional_text(garment_context.get("garment_description")),
            }
            if kind == "garment_description_request":
                next_state["status"] = SESSION_STATE_STATUS_AWAITING_GARMENT_DESCRIPTION
            elif kind == "profile_clarification":
                next_state["status"] = SESSION_STATE_STATUS_AWAITING_PROFILE
            return next_state

        if session_intent == "occasion_outfit":
            return {
                "status": SESSION_STATE_STATUS_COLLECTING_OCCASION if kind == "occasion_clarification" else SESSION_STATE_STATUS_READY,
                "occasion_context": occasion_context,
            }

        return {}

    async def _upsert_session_state(
        self,
        *,
        session: AsyncSession,
        session_id: str,
        session_state: StylistSessionState | None,
        active_intent: SessionIntent | None,
        state_payload: dict[str, Any],
    ) -> None:
        payload = dict(state_payload)
        if active_intent is not None:
            payload["active_intent"] = active_intent

        if session_state is None:
            if active_intent is None and not payload:
                return
            await stylist_session_states_repository.create(
                session,
                {
                    "session_id": session_id,
                    "active_intent": active_intent,
                    "state_payload": payload,
                },
            )
            return

        await stylist_session_states_repository.update(
            session,
            session_state,
            {
                "active_intent": active_intent,
                "state_payload": payload,
            },
        )

    def _resolve_style_seed(
        self,
        *,
        session_id: str,
        user_message: str,
        latest_message: ChatMessage | None,
        session_intent: SessionIntent,
        messages: list[ChatMessage],
    ) -> dict[str, str] | None:
        if session_intent != "style_exploration":
            return None

        if (
            latest_message is not None
            and latest_message.role == ChatMessageRole.ASSISTANT
        ):
            payload = latest_message.payload if isinstance(latest_message.payload, dict) else {}
            existing_seed = payload.get("pending_style_seed") or payload.get("style_seed")
            if (
                payload.get("kind") == "profile_clarification"
                and payload.get("pending_intent") == "style_exploration"
                and isinstance(existing_seed, dict)
                and isinstance(existing_seed.get("slug"), str)
            ):
                canonical_seed = self._find_style_direction_by_slug(str(existing_seed["slug"]))
                if canonical_seed is not None:
                    return canonical_seed

        base_digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        base_index = int(base_digest[:8], 16) % len(STYLE_DIRECTIONS)
        ordered_directions = [
            dict(STYLE_DIRECTIONS[(base_index + offset) % len(STYLE_DIRECTIONS)])
            for offset in range(len(STYLE_DIRECTIONS))
        ]
        used_slugs = self._collect_used_style_slugs(messages)
        used_slug_set = set(used_slugs)

        for direction in ordered_directions:
            if direction["slug"] not in used_slug_set:
                return direction

        last_used_slug = used_slugs[-1] if used_slugs else None
        for direction in ordered_directions:
            if direction["slug"] != last_used_slug:
                return direction

        return ordered_directions[0]

    def _find_style_direction_by_slug(self, slug: str) -> dict[str, str] | None:
        for direction in STYLE_DIRECTIONS:
            if direction["slug"] == slug:
                return dict(direction)
        return None

    def _collect_used_style_slugs(self, messages: list[ChatMessage]) -> list[str]:
        seen_slugs: list[str] = []
        for message in messages:
            if message.role != ChatMessageRole.ASSISTANT:
                continue
            payload = message.payload if isinstance(message.payload, dict) else {}
            seed = payload.get("pending_style_seed") or payload.get("style_seed")
            if not isinstance(seed, dict):
                continue
            slug = seed.get("slug")
            if isinstance(slug, str) and slug not in seen_slugs:
                seen_slugs.append(slug)
        return seen_slugs

    def _collect_previous_style_directions(
        self,
        messages: list[ChatMessage],
        *,
        exclude_slug: str | None = None,
    ) -> list[dict[str, str]]:
        directions: list[dict[str, str]] = []
        for slug in self._collect_used_style_slugs(messages):
            if slug == exclude_slug:
                continue
            direction = self._find_style_direction_by_slug(slug)
            if direction is not None:
                directions.append(
                    {
                        "slug": direction["slug"],
                        "ru": direction["ru"],
                        "en": direction["en"],
                    }
                )
        return directions

    def _requires_profile(self, session_intent: SessionIntent) -> bool:
        return session_intent in {"garment_matching", "style_exploration"}

    def _collect_profile_context(
        self,
        *,
        messages: list[ChatMessage],
        explicit_gender: str | None,
        explicit_height_cm: int | None,
        explicit_weight_kg: int | None,
    ) -> dict[str, str | int | None]:
        gender = explicit_gender
        height_cm = explicit_height_cm
        weight_kg = explicit_weight_kg

        for message in reversed(messages):
            if message.role != ChatMessageRole.USER:
                continue

            payload = message.payload if isinstance(message.payload, dict) else {}
            text = message.content or ""

            if gender is None:
                gender = self._normalize_gender(payload.get("profile_gender")) or self._extract_gender_from_text(text)
            if height_cm is None:
                height_cm = self._coerce_int(payload.get("body_height_cm")) or self._extract_height_cm(text)
            if weight_kg is None:
                weight_kg = self._coerce_int(payload.get("body_weight_kg")) or self._extract_weight_kg(text)

            if gender and height_cm and weight_kg:
                break

        return {
            "gender": gender,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
        }

    def _build_conversation_history(self, messages: list[ChatMessage], limit: int = 6) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for message in messages[-limit:]:
            if not message.content:
                continue
            role = "assistant"
            if message.role == ChatMessageRole.USER:
                role = "user"
            elif message.role == ChatMessageRole.SYSTEM:
                role = "system"
            history.append({"role": role, "content": message.content.strip()[:280]})
        return history

    def _get_missing_profile_fields(self, profile_context: dict[str, str | int | None]) -> tuple[str, ...]:
        missing: list[str] = []
        if not profile_context.get("gender"):
            missing.append("gender")
        if not self._coerce_int(profile_context.get("height_cm")):
            missing.append("height_cm")
        if not self._coerce_int(profile_context.get("weight_kg")):
            missing.append("weight_kg")
        return tuple(missing)

    def _normalize_gender(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        lowered = value.strip().lower()
        male_values = {
            "male",
            "man",
            "masculine",
            "m",
            "м",
            "муж",
            "мужчина",
            "парень",
            "юноша",
        }
        female_values = {
            "female",
            "woman",
            "feminine",
            "f",
            "ж",
            "жен",
            "женщина",
            "девушка",
        }

        if lowered in male_values:
            return "male"
        if lowered in female_values:
            return "female"
        return None

    def _extract_gender_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        male_patterns = (
            r"\bмужчина\b",
            r"\bпарень\b",
            r"\bюноша\b",
            r"\bmale\b",
            r"\bman\b",
            r"\bguy\b",
        )
        female_patterns = (
            r"\bженщина\b",
            r"\bдевушка\b",
            r"\bfemale\b",
            r"\bwoman\b",
            r"\bgirl\b",
        )

        if any(re.search(pattern, lowered) for pattern in male_patterns):
            return "male"
        if any(re.search(pattern, lowered) for pattern in female_patterns):
            return "female"
        return None

    def _extract_height_cm(self, text: str) -> int | None:
        lowered = text.lower()
        match = re.search(r"(?:(?:рост)|height)\s*[:\-]?\s*(\d{2,3})", lowered)
        if match:
            return self._validate_height(int(match.group(1)))

        match = re.search(r"\b(\d{3})\s*(?:см|cm)\b", lowered)
        if match:
            return self._validate_height(int(match.group(1)))

        match = re.search(r"\b(1[.,]\d{2})\s*(?:м|m)\b", lowered)
        if match:
            meters_value = float(match.group(1).replace(",", "."))
            return self._validate_height(round(meters_value * 100))

        return None

    def _extract_weight_kg(self, text: str) -> int | None:
        lowered = text.lower()
        match = re.search(r"(?:(?:вес)|weight)\s*[:\-]?\s*(\d{2,3})", lowered)
        if match:
            return self._validate_weight(int(match.group(1)))

        match = re.search(r"\b(\d{2,3})\s*(?:кг|kg)\b", lowered)
        if match:
            return self._validate_weight(int(match.group(1)))

        return None

    def _validate_height(self, value: int) -> int | None:
        return value if 120 <= value <= 230 else None

    def _validate_weight(self, value: int) -> int | None:
        return value if 35 <= value <= 250 else None

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def _resolve_route(
        self,
        *,
        requested_route: StylistRoute,
        auto_generate: bool,
        session_intent: SessionIntent,
    ) -> StylistRoute:
        if requested_route == "text_and_catalog":
            return "text_and_catalog"
        if auto_generate and (
            requested_route == "text_and_generation" or session_intent in {"garment_matching", "style_exploration"}
        ):
            return "text_and_generation"
        return "text_only"

    def _build_generation_prompt(
        self,
        *,
        user_message: str,
        image_brief_en: str,
        asset: UploadedAsset | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        profile_context: dict[str, str | int | None],
        session_intent: SessionIntent,
        style_seed: dict[str, str] | None,
        occasion_context: dict[str, str] | None,
    ) -> str:
        compact_asset_name = ""
        if asset is not None:
            compact_asset_name = re.sub(r"\s+", " ", asset.original_filename).strip()
            compact_asset_name = compact_asset_name.rsplit(".", 1)[0]
            compact_asset_name = compact_asset_name[:48].strip(" -_.")

        asset_part = ""
        if compact_asset_name:
            asset_part = (
                f" Anchor around the uploaded item {compact_asset_name}. "
            )

        body_part = ""
        if body_height_cm or body_weight_kg:
            body_part = (
                f" Proportion hint only: {body_height_cm or 'n/a'} cm, {body_weight_kg or 'n/a'} kg. "
            )

        gender_part = ""
        if profile_context.get("gender") == "male":
            gender_part = (
                " Menswear proportions only. Strict menswear only: no womenswear garments, no dresses, skirts, bras, "
                "crop tops, heels, handbags, or feminine-coded accessories. "
            )
        elif profile_context.get("gender") == "female":
            gender_part = (
                " Womenswear proportions only. Strict womenswear only: no menswear-only tailoring cues, no menswear "
                "footwear, and no masculine-coded accessories unless explicitly requested. "
            )

        style_part = ""
        if style_seed is not None:
            style_part = (
                f" Style: {style_seed['en']}; {style_seed['descriptor']}. "
            )
        elif session_intent == "general_advice":
            style_part = " Follow the user's mood and context. "

        compact_brief = re.sub(r"\s+", " ", image_brief_en).strip()
        if compact_brief:
            brief_words = compact_brief.split()
            if len(brief_words) > 22:
                compact_brief = " ".join(brief_words[:22])
        compact_brief = compact_brief or "cohesive editorial outfit"

        compact_request = re.sub(r"\s+", " ", user_message).strip()
        skip_request_context = (
            not compact_request
            or asset is not None
            or compact_request == "Need outfit guidance"
            or compact_request == "Нужна рекомендация по образу"
        )
        if compact_request and not skip_request_context:
            request_words = compact_request.split()
            if len(request_words) > 8:
                compact_request = " ".join(request_words[:8])

        request_part = ""
        if compact_request and not skip_request_context:
            request_part = f" User context: {compact_request}. "

        occasion_part = ""
        if session_intent == "occasion_outfit" and occasion_context:
            compact_occasion_bits = [
                f"{field.replace('_', ' ')}: {value}"
                for field, value in occasion_context.items()
                if value
            ]
            if compact_occasion_bits:
                occasion_part = f" Occasion context: {'; '.join(compact_occasion_bits[:4])}. "

        prompt = (
            "Luxury editorial flat lay, overhead, garments only; no model, mannequin, body parts, text, logos, collage, props, hanger, or watermark. "
            "One complete outfit only, 4 to 6 items max: outer/top/bottom or one dress/suit, one pair of shoes, one bag, max one clear accessory. "
            "No duplicates, cropped pieces, floating extras, broken tailoring, deformed shoes, or ambiguous accessories. "
            "Keep every item fully visible, readable, and coherent. "
            f"Brief: {compact_brief}. "
            f"{request_part}{occasion_part}{asset_part}{body_part}{gender_part}{style_part}"
        ).strip()
        prompt_words = prompt.split()
        if len(prompt_words) > 95:
            prompt = " ".join(prompt_words[:95])
        return prompt

    def _should_create_generation_job(self, *, auto_generate: bool, route: StylistRoute) -> bool:
        return auto_generate and route == "text_and_generation"

    def _build_garment_description_request_decision(self, *, locale: str) -> StylistDecision:
        reply_ru = (
            "Опишите вещь, вокруг которой нужно собрать образ: что это за предмет, какого он цвета, "
            "из какого материала и как сидит. Достаточно одной короткой строки, например: "
            "темно-синяя джинсовая рубашка прямого кроя."
        )
        reply_en = (
            "Describe the garment you want to build the outfit around: what it is, the color, "
            "the material, and the fit. One short line is enough, for example: "
            "a dark-blue straight-fit denim shirt."
        )
        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en="",
            generation_prompt_en="",
            route="text_only",
            provider="garment_gate",
            metadata={
                "kind": "garment_description_request",
                "pending_intent": "garment_matching",
                "pending_generation": True,
                "primary_reply": primary_reply,
            },
        )

    def _build_occasion_clarification_decision(
        self,
        *,
        locale: str,
        pending_generation: bool,
        occasion_context: dict[str, str],
    ) -> StylistDecision:
        known_bits: list[str] = []
        for field in ("venue", "dress_code", "time_of_day", "desired_impression"):
            value = self._optional_text(occasion_context.get(field))
            if not value:
                continue
            label_ru = {
                "venue": "площадка",
                "dress_code": "дресс-код",
                "time_of_day": "время",
                "desired_impression": "настроение",
            }[field]
            label_en = {
                "venue": "venue",
                "dress_code": "dress code",
                "time_of_day": "time",
                "desired_impression": "mood",
            }[field]
            known_bits.append(
                f"{label_ru}: {value}" if locale == "ru" else f"{label_en}: {value}"
            )

        context_suffix = ""
        if known_bits:
            context_suffix = (
                f" Уже вижу: {', '.join(known_bits)}."
                if locale == "ru"
                else f" I already have: {', '.join(known_bits)}."
            )

        reply_ru = (
            "С радостью помогу. Сначала уточните, пожалуйста, что это за мероприятие: "
            "свадьба, свидание, ужин, корпоратив, театр, вечеринка или что-то другое. "
            "Если знаете, можно сразу добавить время суток и дресс-код."
        ) + context_suffix
        reply_en = (
            "Happy to help. First, tell me what kind of event it is: a wedding, date, dinner, "
            "work event, theater night, party, or something else. If you know it, you can also "
            "add the time of day and dress code."
        ) + context_suffix
        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en="",
            generation_prompt_en="",
            route="text_only",
            provider="occasion_gate",
            metadata={
                "kind": "occasion_clarification",
                "pending_intent": "occasion_outfit",
                "pending_generation": pending_generation,
                "primary_reply": primary_reply,
                "occasion_context": occasion_context,
            },
        )

    def _build_existing_generation_job_decision(
        self,
        *,
        locale: str,
        existing_job,
        fallback_decision: StylistDecision,
    ) -> StylistDecision:
        if existing_job.status == GenerationStatus.PENDING:
            reply_ru = (
                "У вас уже есть задача на генерацию изображения. Она стоит в очереди, поэтому новый "
                "запрос на картинку я сейчас не запускаю."
            )
            reply_en = (
                "You already have an image generation task. It is waiting in the queue, so I am not "
                "starting another image request right now."
            )
        else:
            reply_ru = (
                "У вас уже есть активная генерация изображения. Дождитесь её завершения; пока можно "
                "продолжать переписку текстом."
            )
            reply_en = (
                "You already have an active image generation task. Let it finish first; in the meantime "
                "we can continue chatting in text."
            )

        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            image_brief_en=fallback_decision.image_brief_en,
            generation_prompt_en=fallback_decision.generation_prompt_en,
            route="text_only",
            provider="generation_guard",
            model=fallback_decision.model,
            metadata={
                **fallback_decision.metadata,
                "kind": "existing_generation_job_notice",
                "existing_generation_job_public_id": existing_job.public_id,
            },
        )


stylist_service = StylistService()
