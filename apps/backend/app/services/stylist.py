from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ChatMessageRole
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate
from app.schemas.stylist import StylistMessageRequest
from app.services.generation import generation_service


class StylistService:
    async def process_message(self, session: AsyncSession, payload: StylistMessageRequest):
        latest_user_message = await chat_messages_repository.get_latest_user_message(session, payload.session_id)
        if latest_user_message:
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

        user_message_text = payload.message or (
            f"Uploaded wardrobe item: {asset.original_filename}" if asset else "Need a new styled outfit"
        )

        await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.USER,
                "locale": payload.locale,
                "content": user_message_text,
                "uploaded_asset_id": payload.uploaded_asset_id,
                "payload": {
                    "body_height_cm": payload.body_height_cm,
                    "body_weight_kg": payload.body_weight_kg,
                },
            },
        )

        recommendation = self._build_recommendation(
            message=user_message_text,
            locale=payload.locale,
            body_height_cm=payload.body_height_cm,
            body_weight_kg=payload.body_weight_kg,
        )
        prompt = self._build_prompt(user_message_text, recommendation["en"], payload.body_height_cm, payload.body_weight_kg)

        generation_job = None
        if payload.auto_generate:
            generation_job = await generation_service.create_and_submit(
                session,
                GenerationJobCreate(
                    session_id=payload.session_id,
                    input_text=user_message_text,
                    recommendation_ru=recommendation["ru"],
                    recommendation_en=recommendation["en"],
                    prompt=prompt,
                    input_asset_id=payload.uploaded_asset_id,
                    body_height_cm=payload.body_height_cm,
                    body_weight_kg=payload.body_weight_kg,
                ),
            )

        assistant_message = await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.ASSISTANT,
                "locale": payload.locale,
                "content": recommendation[payload.locale if payload.locale in {"ru", "en"} else "en"],
                "generation_job_id": generation_job.id if generation_job else None,
                "payload": {"prompt": prompt},
            },
        )
        assistant_message = await chat_messages_repository.get_with_relations(session, assistant_message.id)
        if assistant_message is None:
            raise RuntimeError("Assistant message was not found after creation")
        await chat_messages_repository.trim_session(session, payload.session_id, keep_latest=50)

        return {
            "session_id": payload.session_id,
            "recommendation_text": recommendation[payload.locale if payload.locale in {"ru", "en"} else "en"],
            "recommendation_text_ru": recommendation["ru"],
            "recommendation_text_en": recommendation["en"],
            "prompt": prompt,
            "assistant_message": assistant_message,
            "generation_job": generation_job,
            "timestamp": datetime.now(UTC),
        }

    async def get_history(self, session: AsyncSession, session_id: str):
        return await chat_messages_repository.list_by_session(session, session_id, limit=50)

    def _build_recommendation(
        self, *, message: str, locale: str, body_height_cm: int | None, body_weight_kg: int | None
    ) -> dict[str, str]:
        lowered = message.lower()
        if any(keyword in lowered for keyword in ["shirt", "рубаш", "tee", "футбол"]):
            base_ru = "Добавлю структурированный overshirt и светлые прямые брюки, чтобы образ выглядел собранно."
            base_en = "I would add a structured overshirt and light straight-leg trousers for a more composed look."
        elif any(keyword in lowered for keyword in ["hat", "шляп", "cap", "кепк"]):
            base_ru = "Сюда хорошо подойдет легкая куртка и контрастный аксессуар, чтобы собрать силуэт."
            base_en = "A light jacket and a contrasting accessory would complete the silhouette well."
        else:
            base_ru = "Предлагаю собрать спокойный smart-casual flat-lay с фактурным верхом, чистыми базовыми брюками и акцентным аксессуаром."
            base_en = "I suggest a calm smart-casual flat-lay with a textured top, clean tailored trousers and one accent accessory."

        body_hint_ru = ""
        body_hint_en = ""
        if body_height_cm or body_weight_kg:
            body_hint_ru = f" Учитываю пропорции тела: рост {body_height_cm or 'не указан'} см, вес {body_weight_kg or 'не указан'} кг."
            body_hint_en = (
                f" I am considering body proportions: height {body_height_cm or 'n/a'} cm, weight {body_weight_kg or 'n/a'} kg."
            )

        return {"ru": base_ru + body_hint_ru, "en": base_en + body_hint_en}

    def _build_prompt(
        self, message: str, recommendation_en: str, body_height_cm: int | None, body_weight_kg: int | None
    ) -> str:
        body_part = ""
        if body_height_cm or body_weight_kg:
            body_part = (
                f" Body metrics hint: height {body_height_cm or 'n/a'} cm, weight {body_weight_kg or 'n/a'} kg."
            )
        return (
            "Luxury editorial flat-lay fashion composition on premium textured surface, soft studio light, "
            "clean shadows, modern wardrobe styling, premium color palette, neatly arranged clothes and accessories. "
            f"User input: {message}. Stylist recommendation: {recommendation_en}.{body_part}"
        )


stylist_service = StylistService()
