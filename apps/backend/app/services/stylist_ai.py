import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.vllm import VLLMClient, VLLMClientError
from app.models.chat_message import ChatMessage
from app.models.enums import ChatMessageRole
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate
from app.schemas.stylist import StylistMessageRequest
from app.services.generation import generation_service

logger = logging.getLogger(__name__)

StylistRoute = Literal["text_only", "text_and_generation", "text_and_catalog"]

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
CATALOG_HINTS = (
    "buy",
    "shop",
    "catalog",
    "where can i get",
    "what should i buy",
    "куп",
    "каталог",
    "что купить",
    "где купить",
)


@dataclass
class StylistDecision:
    reply_ru: str
    reply_en: str
    generation_prompt_en: str
    route: StylistRoute
    provider: str
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


GENERATION_HINTS = (
    "generate",
    "render",
    "visualize",
    "visualise",
    "lookbook",
    "flat-lay",
    "flat lay",
    "\u0441\u0433\u0435\u043d\u0435\u0440",
    "\u0432\u0438\u0437\u0443\u0430\u043b",
    "\u043f\u043e\u043a\u0430\u0436\u0438 \u043f\u0440\u0438\u043c\u0435\u0440",
    "\u043f\u0440\u0438\u043c\u0435\u0440 \u043e\u0431\u0440\u0430\u0437\u0430",
)

CATALOG_HINTS = (
    "buy",
    "shop",
    "catalog",
    "where can i get",
    "what should i buy",
    "\u043a\u0443\u043f",
    "\u043a\u0430\u0442\u0430\u043b\u043e\u0433",
    "\u0447\u0442\u043e \u043a\u0443\u043f\u0438\u0442\u044c",
    "\u0433\u0434\u0435 \u043a\u0443\u043f\u0438\u0442\u044c",
)


class StylistService:
    def __init__(self) -> None:
        self.vllm_client = VLLMClient()

    async def process_message(self, session: AsyncSession, payload: StylistMessageRequest):
        locale = payload.locale if payload.locale in {"ru", "en"} else "en"

        latest_messages = await chat_messages_repository.list_by_session(session, payload.session_id, limit=2)
        latest_message = latest_messages[-1] if latest_messages else None
        latest_user_message = await chat_messages_repository.get_latest_user_message(session, payload.session_id)
        if latest_user_message and not self._should_skip_cooldown(latest_message):
            next_available_at = latest_user_message.created_at + timedelta(minutes=1)
            remaining_seconds = int((next_available_at - datetime.now(UTC)).total_seconds())
            if remaining_seconds > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Please wait before sending the next message.",
                        "retry_after_seconds": remaining_seconds,
                    },
                )

        asset = None
        if payload.uploaded_asset_id:
            asset = await uploads_repository.get(session, payload.uploaded_asset_id)
            if asset is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded asset was not found.")

        user_message_text = payload.message or (
            f"Uploaded wardrobe item: {asset.original_filename}" if asset else "Need a new styled outfit"
        )
        normalized_gender = self._normalize_gender(payload.profile_gender)

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
                },
            },
        )

        conversation_messages = await chat_messages_repository.list_by_session(session, payload.session_id, limit=12)
        profile_context = self._collect_profile_context(
            messages=conversation_messages,
            explicit_gender=normalized_gender,
            explicit_height_cm=payload.body_height_cm,
            explicit_weight_kg=payload.body_weight_kg,
        )
        resolved_height_cm = self._coerce_int(profile_context.get("height_cm"))
        resolved_weight_kg = self._coerce_int(profile_context.get("weight_kg"))
        missing_profile_fields = self._get_missing_profile_fields(profile_context)

        if missing_profile_fields:
            decision = self._build_profile_clarification_decision(
                locale=locale,
                missing_fields=missing_profile_fields,
                profile_context=profile_context,
            )
        else:
            decision = await self._make_stylist_decision(
                locale=locale,
                user_message=user_message_text,
                uploaded_asset_name=asset.original_filename if asset else None,
                body_height_cm=resolved_height_cm,
                body_weight_kg=resolved_weight_kg,
                auto_generate=payload.auto_generate,
                conversation_history=self._build_conversation_history(conversation_messages),
                profile_context=profile_context,
            )

        generation_job = None
        if self._should_create_generation_job(
            auto_generate=payload.auto_generate,
            route=decision.route,
        ):
            generation_job = await generation_service.create_and_submit(
                session,
                GenerationJobCreate(
                    session_id=payload.session_id,
                    input_text=user_message_text,
                    recommendation_ru=decision.reply_ru,
                    recommendation_en=decision.reply_en,
                    prompt=decision.generation_prompt_en,
                    input_asset_id=payload.uploaded_asset_id,
                    body_height_cm=resolved_height_cm,
                    body_weight_kg=resolved_weight_kg,
                ),
            )

        response_text = decision.reply_ru if locale == "ru" else decision.reply_en
        assistant_payload = {
            "prompt": decision.generation_prompt_en,
            "route": decision.route,
            "provider": decision.provider,
            "model": decision.model,
            **decision.metadata,
        }
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
        return await chat_messages_repository.list_by_session(session, session_id, limit=50)

    async def _make_stylist_decision(
        self,
        *,
        locale: str,
        user_message: str,
        uploaded_asset_name: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        conversation_history: list[dict[str, str]],
        profile_context: dict[str, str | int | None],
    ) -> StylistDecision:
        try:
            result = await self.vllm_client.generate_stylist_response(
                locale=locale,
                user_message=user_message,
                uploaded_asset_name=uploaded_asset_name,
                body_height_cm=body_height_cm,
                body_weight_kg=body_weight_kg,
                auto_generate=auto_generate,
                conversation_history=conversation_history,
                profile_context=profile_context,
                session_intent="general_advice",
                style_seed=None,
                previous_style_directions=[],
            )
            return StylistDecision(
                reply_ru=result.reply_ru,
                reply_en=result.reply_en,
                generation_prompt_en=self._build_generation_prompt(
                    user_message=user_message,
                    recommendation_en=result.reply_en,
                    uploaded_asset_name=uploaded_asset_name,
                    body_height_cm=body_height_cm,
                    body_weight_kg=body_weight_kg,
                    profile_context=profile_context,
                ),
                route=self._resolve_route(
                    requested_route=result.route,
                    auto_generate=auto_generate,
                ),
                provider="vllm",
                model=result.model,
                metadata={"profile_context": profile_context},
            )
        except VLLMClientError as exc:
            logger.warning("vLLM is unavailable, using deterministic fallback: %s", exc)
            return self._build_fallback_decision_clean(
                user_message=user_message,
                body_height_cm=body_height_cm,
                body_weight_kg=body_weight_kg,
                auto_generate=auto_generate,
                uploaded_asset_name=uploaded_asset_name,
                profile_context=profile_context,
            )

    def _build_fallback_decision(
        self,
        *,
        user_message: str,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        uploaded_asset_name: str | None,
    ) -> StylistDecision:
        lowered = user_message.lower()

        if any(keyword in lowered for keyword in ("shirt", "рубаш", "tee", "футбол")):
            reply_ru = "К базе добавлю структурированный верхний слой и светлые прямые брюки, чтобы образ выглядел собранно."
            reply_en = "I would add a structured outer layer and light straight-leg trousers so the outfit feels more composed."
        elif any(keyword in lowered for keyword in ("hat", "шляп", "cap", "кепк")):
            reply_ru = "Сюда хорошо подойдет легкая куртка и контрастный аксессуар, чтобы силуэт выглядел цельно."
            reply_en = "A light jacket and one contrasting accessory would make the silhouette feel more complete."
        else:
            reply_ru = "Я бы собрал спокойный smart-casual образ с фактурным верхом, чистой базой и одним выразительным акцентом."
            reply_en = "I would build a calm smart-casual look with a textured top, a clean base, and one expressive accent."

        if body_height_cm or body_weight_kg:
            reply_ru += (
                f" Учитываю пропорции тела: рост {body_height_cm or 'не указан'} см, "
                f"вес {body_weight_kg or 'не указан'} кг."
            )
            reply_en += (
                f" I am also factoring in body proportions: height {body_height_cm or 'n/a'} cm, "
                f"weight {body_weight_kg or 'n/a'} kg."
            )

        route = self._detect_fallback_route(
            user_message=user_message,
            uploaded_asset_name=uploaded_asset_name,
            auto_generate=auto_generate,
        )
        generation_prompt_en = self._build_generation_prompt(
            user_message=user_message,
            recommendation_en=reply_en,
            uploaded_asset_name=uploaded_asset_name,
            body_height_cm=body_height_cm,
            body_weight_kg=body_weight_kg,
            profile_context={},
        )

        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            generation_prompt_en=generation_prompt_en,
            route=route,
            provider="fallback",
        )

    def _build_fallback_decision_clean(
        self,
        *,
        user_message: str,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        uploaded_asset_name: str | None,
        profile_context: dict[str, str | int | None],
    ) -> StylistDecision:
        lowered = user_message.lower()

        if any(keyword in lowered for keyword in ("hoodie", "hoodies", "\u0442\u043e\u043b\u0441\u0442\u043e\u0432\u043a", "\u0441\u0432\u0438\u0442\u0448\u043e\u0442")):
            reply_ru = (
                "\u042f \u0431\u044b \u043d\u0435 \u043b\u043e\u043c\u0430\u043b \u043f\u0440\u0438\u0432\u044b\u0447\u043d\u044b\u0439 "
                "\u0441\u0442\u0438\u043b\u044c \u0440\u0435\u0437\u043a\u043e: \u043d\u0430\u0447\u0430\u043b \u0431\u044b \u0441 "
                "\u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043e\u0442 \u0445\u0443\u0434\u0438 \u043a \u0442\u043e\u043d\u043a\u043e\u043c\u0443 "
                "\u043f\u0443\u043b\u043e\u0432\u0435\u0440\u0443, \u0442\u0440\u0438\u043a\u043e\u0442\u0430\u0436\u043d\u043e\u043c\u0443 "
                "\u043f\u043e\u043b\u043e \u0438\u043b\u0438 \u0431\u043e\u043b\u0435\u0435 \u0447\u0438\u0441\u0442\u043e\u043c\u0443 "
                "\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043d\u043e\u043c\u0443 \u0432\u0435\u0440\u0445\u043d\u0435\u043c\u0443 \u0441\u043b\u043e\u044e. "
                "\u041d\u0438\u0436\u0435 \u043f\u043e\u0441\u0442\u0430\u0432\u0438\u043b \u0431\u044b \u043f\u0440\u044f\u043c\u044b\u0435 "
                "\u0431\u0440\u044e\u043a\u0438 \u0438\u043b\u0438 \u0442\u0435\u043c\u043d\u044b\u0435 \u0447\u0438\u043d\u043e\u0441\u044b, "
                "\u0447\u0442\u043e\u0431\u044b \u043e\u0431\u0440\u0430\u0437 \u0441\u0442\u0430\u043b \u0432\u0437\u0440\u043e\u0441\u043b\u0435\u0435 \u0438 "
                "\u0441\u043e\u0431\u0440\u0430\u043d\u043d\u0435\u0435."
            )
            reply_en = (
                "I would not force a hard style switch at once: I would move from hoodies toward a fine-gauge "
                "pullover, a knit polo, or a cleaner structured top layer. Underneath, I would anchor the outfit "
                "with straight trousers or dark chinos so it feels sharper and more grown-up."
            )
        elif any(keyword in lowered for keyword in ("shirt", "\u0440\u0443\u0431\u0430\u0448", "tee", "\u0431\u043b\u0443\u0437")):
            reply_ru = (
                "\u042f \u0431\u044b \u0441\u043e\u0431\u0440\u0430\u043b \u043e\u0431\u0440\u0430\u0437 \u0432\u043e\u043a\u0440\u0443\u0433 "
                "\u0440\u0443\u0431\u0430\u0448\u043a\u0438 \u0438 \u0434\u043e\u0431\u0430\u0432\u0438\u043b \u043a \u043d\u0435\u0439 "
                "\u0440\u043e\u0432\u043d\u044b\u0435 \u0431\u0440\u044e\u043a\u0438, \u0441\u043f\u043e\u043a\u043e\u0439\u043d\u044b\u0439 "
                "\u0442\u0440\u0438\u043a\u043e\u0442\u0430\u0436 \u0438 \u0447\u0438\u0441\u0442\u0443\u044e \u043e\u0431\u0443\u0432\u044c. "
                "\u0422\u0430\u043a \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0442 \u043e\u0441\u0442\u0430\u043d\u0435\u0442\u0441\u044f "
                "\u0432 \u043a\u043b\u0430\u0441\u0441\u0438\u0447\u0435\u0441\u043a\u043e\u043c \u0438\u043b\u0438 \u0434\u0435\u043b\u043e\u0432\u043e\u043c "
                "\u043f\u043e\u043b\u0435, \u043d\u043e \u043d\u0435 \u0431\u0443\u0434\u0435\u0442 \u0432\u044b\u0433\u043b\u044f\u0434\u0435\u0442\u044c "
                "\u0447\u0435\u0440\u0435\u0441\u0447\u0443\u0440 \u0441\u0442\u0440\u043e\u0433\u0438\u043c."
            )
            reply_en = (
                "I would build the outfit around the shirt and pair it with clean trousers, restrained knitwear, "
                "and polished footwear. That keeps the look in a classic or business lane without making it feel overly rigid."
            )
        else:
            reply_ru = (
                "\u042f \u0431\u044b \u0434\u0435\u0440\u0436\u0430\u043b \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 "
                "\u0432 \u0441\u0442\u043e\u0440\u043e\u043d\u0443 \u043a\u043b\u0430\u0441\u0441\u0438\u0447\u0435\u0441\u043a\u043e\u0433\u043e "
                "\u0438 \u0434\u0435\u043b\u043e\u0432\u043e\u0433\u043e smart-casual: \u0440\u0443\u0431\u0430\u0448\u043a\u0430 "
                "\u0438\u043b\u0438 \u0442\u043e\u043d\u043a\u0438\u0439 \u0442\u0440\u0438\u043a\u043e\u0442\u0430\u0436, \u0440\u043e\u0432\u043d\u044b\u0435 "
                "\u0431\u0440\u044e\u043a\u0438, \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043d\u044b\u0439 \u0432\u0435\u0440\u0445\u043d\u0438\u0439 "
                "\u0441\u043b\u043e\u0439 \u0438 \u0441\u043f\u043e\u043a\u043e\u0439\u043d\u0430\u044f \u043a\u043e\u0436\u0430\u043d\u0430\u044f "
                "\u043e\u0431\u0443\u0432\u044c. \u0415\u0441\u043b\u0438 \u043f\u043e\u043b\u043d\u0430\u044f \u043a\u043b\u0430\u0441\u0441\u0438\u043a\u0430 "
                "\u043f\u043e\u043a\u0430 \u043d\u0435\u043f\u0440\u0438\u0432\u044b\u0447\u043d\u0430, \u043d\u0430\u0447\u043d\u0435\u043c "
                "\u043c\u044f\u0433\u0447\u0435: \u0437\u0430\u043c\u0435\u043d\u0438\u043c \u0445\u0443\u0434\u0438 \u043d\u0430 "
                "\u043f\u0443\u043b\u043e\u0432\u0435\u0440 \u0438 \u043f\u043e\u0441\u0442\u0435\u043f\u0435\u043d\u043d\u043e \u0441\u043e\u0431\u0435\u0440\u0435\u043c "
                "\u0431\u043e\u043b\u0435\u0435 \u0447\u0438\u0441\u0442\u044b\u0439 \u0441\u0438\u043b\u0443\u044d\u0442."
            )
            reply_en = (
                "I would steer the look toward classic and business smart-casual: a shirt or fine knitwear, "
                "clean trousers, a structured top layer, and understated leather footwear. If full tailoring feels "
                "too formal for now, I would start with a softer transition by replacing hoodies with a pullover "
                "and cleaning up the silhouette step by step."
            )

        if body_height_cm or body_weight_kg:
            height_hint = body_height_cm if body_height_cm is not None else "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d"
            weight_hint = body_weight_kg if body_weight_kg is not None else "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d"
            reply_ru += (
                f" \u0423\u0447\u0438\u0442\u044b\u0432\u0430\u044e \u043f\u0440\u043e\u043f\u043e\u0440\u0446\u0438\u0438 "
                f"\u0442\u0435\u043b\u0430: \u0440\u043e\u0441\u0442 {height_hint} \u0441\u043c, "
                f"\u0432\u0435\u0441 {weight_hint} \u043a\u0433."
            )
            reply_en += (
                f" I am also factoring in body proportions: height {body_height_cm or 'n/a'} cm, "
                f"weight {body_weight_kg or 'n/a'} kg."
            )

        route = self._detect_fallback_route(
            user_message=user_message,
            uploaded_asset_name=uploaded_asset_name,
            auto_generate=auto_generate,
        )
        generation_prompt_en = self._build_generation_prompt(
            user_message=user_message,
            recommendation_en=reply_en,
            uploaded_asset_name=uploaded_asset_name,
            body_height_cm=body_height_cm,
            body_weight_kg=body_weight_kg,
            profile_context=profile_context,
        )

        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            generation_prompt_en=generation_prompt_en,
            route=route,
            provider="fallback",
            metadata={"profile_context": profile_context},
        )

    def _build_profile_clarification_decision(
        self,
        *,
        locale: str,
        missing_fields: tuple[str, ...],
        profile_context: dict[str, str | int | None],
    ) -> StylistDecision:
        missing_labels_ru = {
            "gender": "\u043f\u043e\u043b",
            "height_cm": "\u0440\u043e\u0441\u0442",
            "weight_kg": "\u0432\u0435\u0441",
        }
        missing_labels_en = {
            "gender": "gender",
            "height_cm": "height",
            "weight_kg": "weight",
        }

        missing_ru = ", ".join(missing_labels_ru[field] for field in missing_fields)
        missing_en = ", ".join(missing_labels_en[field] for field in missing_fields)

        reply_ru = (
            f"\u041f\u0440\u0435\u0436\u0434\u0435 \u0447\u0435\u043c \u043f\u0440\u0435\u0434\u043b\u0430\u0433\u0430\u0442\u044c "
            f"\u043e\u0431\u0440\u0430\u0437, \u043c\u043d\u0435 \u043d\u0443\u0436\u043d\u043e \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c: {missing_ru}. "
            "\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u044d\u0442\u043e \u043e\u0434\u043d\u0438\u043c "
            "\u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435\u043c, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: "
            "\u043c\u0443\u0436\u0447\u0438\u043d\u0430, 182 \u0441\u043c, 78 \u043a\u0433. "
            "\u0411\u0430\u0437\u043e\u0432\u043e \u044f \u0431\u0443\u0434\u0443 \u0441\u043e\u0431\u0438\u0440\u0430\u0442\u044c "
            "\u0431\u043e\u043b\u0435\u0435 \u043a\u043b\u0430\u0441\u0441\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u0438 "
            "\u0434\u0435\u043b\u043e\u0432\u043e\u0435 \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: "
            "\u0431\u0440\u044e\u043a\u0438, \u0440\u0443\u0431\u0430\u0448\u043a\u0438, \u0442\u0440\u0438\u043a\u043e\u0442\u0430\u0436, \u043f\u0438\u0434\u0436\u0430\u043a. "
            "\u0415\u0441\u043b\u0438 \u0432\u044b \u043d\u0435 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u0435 \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u0443\u044e \u0432\u0435\u0449\u044c \u0438\u043b\u0438 \u0441\u0442\u0438\u043b\u044c, \u044f \u0432\u043e\u0437\u044c\u043c\u0443 \u0437\u0430 \u043e\u0441\u043d\u043e\u0432\u0443 \u043f\u043e\u0432\u0441\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0439 \u0434\u0435\u043b\u043e\u0432\u043e\u0439 \u0432\u0430\u0440\u0438\u0430\u043d\u0442. "
            "\u0415\u0441\u043b\u0438 \u0441\u0442\u0440\u043e\u0433\u0430\u044f \u043a\u043b\u0430\u0441\u0441\u0438\u043a\u0430 "
            "\u043f\u043e\u043a\u0430 \u043d\u0435\u043f\u0440\u0438\u0432\u044b\u0447\u043d\u0430, \u043f\u043e\u0439\u0434\u0435\u043c "
            "\u043c\u044f\u0433\u0447\u0435: \u0432\u043c\u0435\u0441\u0442\u043e \u0445\u0443\u0434\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0435\u043c "
            "\u043f\u0443\u043b\u043e\u0432\u0435\u0440, \u0442\u0440\u0438\u043a\u043e\u0442\u0430\u0436\u043d\u043e\u0435 \u043f\u043e\u043b\u043e "
            "\u0438\u043b\u0438 \u0431\u043e\u043b\u0435\u0435 \u0447\u0438\u0441\u0442\u044b\u0439 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043d\u044b\u0439 \u0432\u0435\u0440\u0445."
        )
        reply_en = (
            f"Before I suggest an outfit, I need to confirm your {missing_en}. "
            "Send it in one line, for example: male, 182 cm, 78 kg. "
            "My default direction will lean classic and business-focused: trousers, shirts, knitwear, and a blazer. "
            "If you do not specify a garment or style, I will start from an everyday business baseline. "
            "If full tailoring feels too formal, we can transition gradually by replacing hoodies with pullovers, knit polos, or cleaner structured layers."
        )

        primary_reply = reply_ru if locale == "ru" else reply_en
        return StylistDecision(
            reply_ru=reply_ru,
            reply_en=reply_en,
            generation_prompt_en="",
            route="text_only",
            provider="profile_gate",
            metadata={
                "kind": "profile_clarification",
                "missing_profile_fields": list(missing_fields),
                "profile_context": profile_context,
                "primary_reply": primary_reply,
            },
        )

    def _should_skip_cooldown(self, latest_message: ChatMessage | None) -> bool:
        if latest_message is None or latest_message.role != ChatMessageRole.ASSISTANT:
            return False
        payload = latest_message.payload if isinstance(latest_message.payload, dict) else {}
        return payload.get("kind") == "profile_clarification"

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

    def _build_conversation_history(self, messages: list[ChatMessage], limit: int = 8) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for message in messages[-limit:]:
            if not message.content:
                continue
            role = "assistant"
            if message.role == ChatMessageRole.USER:
                role = "user"
            elif message.role == ChatMessageRole.SYSTEM:
                role = "system"
            history.append(
                {
                    "role": role,
                    "content": message.content.strip()[:500],
                }
            )
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
            "\u043c",
            "\u043c\u0443\u0436",
            "\u043c\u0443\u0436\u0447\u0438\u043d\u0430",
            "\u043f\u0430\u0440\u0435\u043d\u044c",
            "\u044e\u043d\u043e\u0448\u0430",
        }
        female_values = {
            "female",
            "woman",
            "feminine",
            "f",
            "\u0436",
            "\u0436\u0435\u043d",
            "\u0436\u0435\u043d\u0449\u0438\u043d\u0430",
            "\u0434\u0435\u0432\u0443\u0448\u043a\u0430",
        }

        if lowered in male_values:
            return "male"
        if lowered in female_values:
            return "female"
        return None

    def _extract_gender_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        male_patterns = (
            "\\b\\u043c\\u0443\\u0436\\u0447\\u0438\\u043d\\u0430\\b",
            "\\b\\u043f\\u0430\\u0440\\u0435\\u043d\\u044c\\b",
            "\\b\\u044e\\u043d\\u043e\\u0448\\u0430\\b",
            r"\bmale\b",
            r"\bman\b",
            r"\bguy\b",
        )
        female_patterns = (
            "\\b\\u0436\\u0435\\u043d\\u0449\\u0438\\u043d\\u0430\\b",
            "\\b\\u0434\\u0435\\u0432\\u0443\\u0448\\u043a\\u0430\\b",
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
        match = re.search("(?:(?:\\u0440\\u043e\\u0441\\u0442)|height)\\s*[:\\-]?\\s*(\\d{2,3})", lowered)
        if match:
            return self._validate_height(int(match.group(1)))

        match = re.search("\\b(\\d{3})\\s*(?:\\u0441\\u043c|cm)\\b", lowered)
        if match:
            return self._validate_height(int(match.group(1)))

        match = re.search("\\b(1[.,]\\d{2})\\s*(?:\\u043c|m)\\b", lowered)
        if match:
            meters_value = float(match.group(1).replace(",", "."))
            return self._validate_height(round(meters_value * 100))

        return None

    def _extract_weight_kg(self, text: str) -> int | None:
        lowered = text.lower()
        match = re.search("(?:(?:\\u0432\\u0435\\u0441)|weight)\\s*[:\\-]?\\s*(\\d{2,3})", lowered)
        if match:
            return self._validate_weight(int(match.group(1)))

        match = re.search("\\b(\\d{2,3})\\s*(?:\\u043a\\u0433|kg)\\b", lowered)
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
    ) -> StylistRoute:
        if requested_route == "text_and_catalog":
            return "text_and_catalog"
        if auto_generate:
            return "text_and_generation"
        return "text_only"

    def _detect_fallback_route(
        self,
        *,
        user_message: str,
        uploaded_asset_name: str | None,
        auto_generate: bool,
    ) -> StylistRoute:
        lowered = user_message.lower()
        if any(keyword in lowered for keyword in CATALOG_HINTS):
            return "text_and_catalog"
        if auto_generate:
            return "text_and_generation"
        if uploaded_asset_name is not None or any(keyword in lowered for keyword in GENERATION_HINTS):
            return "text_and_generation"
        return "text_only"

    def _build_generation_prompt(
        self,
        *,
        user_message: str,
        recommendation_en: str,
        uploaded_asset_name: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        profile_context: dict[str, str | int | None],
    ) -> str:
        asset_part = f" Anchor garment: {uploaded_asset_name}." if uploaded_asset_name else ""
        body_part = ""
        if body_height_cm or body_weight_kg:
            body_part = (
                f" Body metrics hint: height {body_height_cm or 'n/a'} cm, weight {body_weight_kg or 'n/a'} kg."
            )

        gender_part = ""
        if profile_context.get("gender") == "male":
            gender_part = " Prefer a menswear-oriented wardrobe vocabulary."
        elif profile_context.get("gender") == "female":
            gender_part = " Prefer a womenswear-oriented wardrobe vocabulary."

        return (
            "Luxury Pinterest-worthy glossy editorial flat lay photographed from directly overhead, garments and accessories only, "
            "no human model, no portrait, no person wearing the look, no mannequin. "
            "Compose one coherent outfit carefully arranged on a clean premium surface such as stone, paper, wood, or fabric backdrop. "
            "Leave breathing room between items, keep spacing elegant, balanced, and magazine-like. "
            "If the user did not lock the wardrobe direction, default to an everyday business outfit. "
            "Direction: refined classic or business smart-casual wardrobe with tailored trousers, crisp shirting, "
            "fine-gauge knitwear, a structured blazer or clean outer layer, polished leather footwear, restrained palette, "
            "premium fabrics, crisp fabric texture, soft luxury studio light, clean shadows, elevated but wearable finish. "
            "If the brief is more casual, translate it toward a cleaner wardrobe by replacing hoodies with pullovers "
            "or other structured knit layers. Avoid clutter, duplicate items, collage layout, warped garments, or chaotic styling. "
            f"User request: {user_message}. "
            f"Stylist direction: {recommendation_en}."
            f"{asset_part}{body_part}{gender_part}"
        )

    def _should_create_generation_job(self, *, auto_generate: bool, route: StylistRoute) -> bool:
        return auto_generate and route == "text_and_generation"


stylist_service = StylistService()
