import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.decision_result import DecisionResult, DecisionType
from app.models import UploadedAsset
from app.models.chat_message import ChatMessage
from app.models.enums import ChatMessageRole, GenerationStatus
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate
from app.schemas.stylist import StylistMessageRequest
from app.services.chat_context_store import chat_context_store
from app.services.chat_mode_resolver import chat_mode_resolver
from app.services.generation import generation_service
from app.services.stylist_orchestrator import stylist_orchestrator


class StylistService:
    async def process_message(self, session: AsyncSession, payload: StylistMessageRequest):
        locale = "ru" if payload.locale == "ru" else "en"
        session_state_record, context = await chat_context_store.load(session, payload.session_id)
        context = await self._sync_context_generation_state(session, context)
        requested_intent = self._coerce_requested_intent(payload.requested_intent)

        recent_messages_before = await chat_messages_repository.list_by_session(session, payload.session_id, limit=20)
        asset = await self._resolve_context_asset(
            session=session,
            payload=payload,
            recent_messages=recent_messages_before,
            context=context,
        )
        user_message_text = self._resolve_user_message_text(locale=locale, message=payload.message, asset=asset)

        if not self._should_skip_cooldown(context=context, requested_intent=requested_intent):
            await self._enforce_message_cooldown(session, payload.session_id, locale)

        user_message = await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.USER,
                "locale": locale,
                "content": user_message_text,
                "uploaded_asset_id": asset.id if asset else None,
                "payload": {
                    "requested_intent": requested_intent.value if requested_intent else None,
                    "command_name": payload.command_name,
                    "command_step": payload.command_step,
                    "metadata": payload.metadata,
                    "profile_gender": self._normalize_gender(payload.profile_gender),
                    "body_height_cm": payload.body_height_cm,
                    "body_weight_kg": payload.body_weight_kg,
                    "asset_id": payload.asset_id or payload.uploaded_asset_id,
                },
            },
        )

        recent_messages = await chat_messages_repository.list_by_session(session, payload.session_id, limit=20)
        profile_context = self._collect_profile_context(
            messages=recent_messages,
            explicit_gender=self._normalize_gender(payload.profile_gender),
            explicit_height_cm=payload.body_height_cm,
            explicit_weight_kg=payload.body_weight_kg,
        )
        resolution = chat_mode_resolver.resolve(
            context=context,
            requested_intent=requested_intent,
            command_name=payload.command_name,
            command_step=payload.command_step,
            metadata=payload.metadata,
        )
        context, decision = await stylist_orchestrator.plan_turn(
            session=session,
            session_id=payload.session_id,
            locale=locale,
            context=context,
            resolution=resolution,
            user_message=user_message_text,
            user_message_id=user_message.id,
            asset=asset,
            recent_messages=recent_messages,
            profile_context=profile_context,
        )

        if decision.decision_type == DecisionType.ERROR_RECOVERABLE:
            context.flow_state = FlowState.RECOVERABLE_ERROR

        session_state_record = await chat_context_store.save(
            session,
            session_id=payload.session_id,
            context=context,
            record=session_state_record,
        )

        generation_job = None
        if decision.requires_generation():
            generation_job, decision = await self._materialize_generation_job(
                session=session,
                locale=locale,
                session_id=payload.session_id,
                context=context,
                decision=decision,
                input_text=user_message_text,
                input_asset=asset,
                profile_context=profile_context,
            )
            session_state_record = await chat_context_store.save(
                session,
                session_id=payload.session_id,
                context=context,
                record=session_state_record,
            )

        assistant_text = decision.text_reply or self._fallback_empty_reply(locale)
        assistant_payload = {
            "decision_type": decision.decision_type.value,
            "active_mode": context.active_mode.value,
            "flow_state": context.flow_state.value,
            "clarification_kind": context.clarification_kind.value if context.clarification_kind else None,
            "prompt": decision.generation_payload.prompt if decision.generation_payload else "",
            "image_brief_en": decision.generation_payload.image_brief_en if decision.generation_payload else "",
            "context_patch": decision.context_patch,
            "kind": decision.decision_type.value,
            "command_name": payload.command_name,
            "command_step": payload.command_step,
        }

        assistant_message = await chat_messages_repository.create(
            session,
            {
                "session_id": payload.session_id,
                "role": ChatMessageRole.ASSISTANT,
                "locale": locale,
                "content": assistant_text,
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

        context.remember(role="assistant", content=assistant_text)
        context.touch(message_id=assistant_message.id)
        session_state_record = await chat_context_store.save(
            session,
            session_id=payload.session_id,
            context=context,
            record=session_state_record,
        )
        await chat_messages_repository.trim_session(session, payload.session_id, keep_latest=50)

        return {
            "session_id": payload.session_id,
            "recommendation_text": assistant_text,
            "prompt": decision.generation_payload.prompt if decision.generation_payload else "",
            "assistant_message": assistant_message,
            "generation_job": generation_job,
            "timestamp": datetime.now(timezone.utc),
            "decision": decision,
            "session_context": context,
        }

    async def get_history(self, session: AsyncSession, session_id: str):
        history = await chat_messages_repository.list_by_session(session, session_id, limit=50)
        for message in history:
            if message.generation_job is not None:
                message.generation_job = await generation_service.enrich_job_runtime(session, message.generation_job)
        return history

    async def get_context(self, session: AsyncSession, session_id: str) -> ChatModeContext:
        _, context = await chat_context_store.load(session, session_id)
        return await self._sync_context_generation_state(session, context)

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

    async def _materialize_generation_job(
        self,
        *,
        session: AsyncSession,
        locale: str,
        session_id: str,
        context: ChatModeContext,
        decision: DecisionResult,
        input_text: str,
        input_asset: UploadedAsset | None,
        profile_context: dict[str, str | int | None],
    ) -> tuple[Any, DecisionResult]:
        existing_job = await generation_jobs_repository.get_latest_active_by_session(session, session_id)
        if existing_job is not None and existing_job.status in {GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING}:
            enriched = await generation_service.enrich_job_runtime(session, existing_job)
            context.current_job_id = enriched.public_id
            context.flow_state = self._flow_state_from_generation_status(enriched.status)
            notice = (
                "У вас уже есть активная генерация изображения. Дождитесь её завершения, и затем можно будет запустить следующую."
                if locale == "ru"
                else "You already have an active image generation task. Let it finish before starting the next one."
            )
            return enriched, DecisionResult(
                decision_type=DecisionType.TEXT_ONLY,
                active_mode=context.active_mode,
                flow_state=context.flow_state,
                text_reply=notice,
                context_patch=decision.context_patch,
            )

        generation_payload = decision.generation_payload
        if generation_payload is None:
            return None, decision

        generation_job = await generation_service.create_and_submit(
            session,
            GenerationJobCreate(
                session_id=session_id,
                input_text=input_text,
                recommendation_ru=decision.text_reply or "",
                recommendation_en=decision.text_reply or "",
                prompt=generation_payload.prompt,
                input_asset_id=input_asset.id if input_asset else None,
                body_height_cm=self._coerce_int(profile_context.get("height_cm")),
                body_weight_kg=self._coerce_int(profile_context.get("weight_kg")),
            ),
        )
        context.current_job_id = generation_job.public_id
        context.generation_intent = generation_payload.generation_intent
        context.last_generation_prompt = generation_payload.prompt
        context.flow_state = self._flow_state_from_generation_status(generation_job.status)
        decision.job_id = generation_job.public_id
        return generation_job, decision

    async def _sync_context_generation_state(self, session: AsyncSession, context: ChatModeContext) -> ChatModeContext:
        if not context.current_job_id:
            return context
        generation_job = await generation_jobs_repository.get_by_public_id(session, context.current_job_id)
        if generation_job is None:
            return context
        context.flow_state = self._flow_state_from_generation_status(generation_job.status)
        return context

    async def _enforce_message_cooldown(self, session: AsyncSession, session_id: str, locale: str) -> None:
        latest_assistant_message = await chat_messages_repository.get_latest_assistant_message(session, session_id)
        if latest_assistant_message is None:
            return
        cooldown_seconds = max(generation_service.settings.chat_message_cooldown_seconds, 0)
        if cooldown_seconds <= 0:
            return
        next_allowed_at = latest_assistant_message.created_at + timedelta(seconds=cooldown_seconds)
        remaining_seconds = int((next_allowed_at - datetime.now(timezone.utc)).total_seconds())
        if remaining_seconds <= 0:
            return
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "message_cooldown",
                "message": (
                    "Отправлять новые сообщения можно не чаще одного раза в минуту. Подождите немного и попробуйте снова."
                    if locale == "ru"
                    else "Messages can only be sent once per minute. Please wait a moment and try again."
                ),
                "retry_after_seconds": remaining_seconds,
                "next_allowed_at": next_allowed_at.isoformat(),
            },
        )

    async def _resolve_context_asset(
        self,
        *,
        session: AsyncSession,
        payload: StylistMessageRequest,
        recent_messages: list[ChatMessage],
        context: ChatModeContext,
    ) -> UploadedAsset | None:
        asset_id = payload.uploaded_asset_id or payload.asset_id
        if asset_id:
            asset = await uploads_repository.get(session, asset_id)
            if asset is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded asset was not found.")
            return asset

        if context.active_mode == ChatMode.GARMENT_MATCHING and context.flow_state in {
            FlowState.AWAITING_ANCHOR_GARMENT,
            FlowState.AWAITING_CLARIFICATION,
            FlowState.READY_FOR_DECISION,
            FlowState.READY_FOR_GENERATION,
        }:
            for message in reversed(recent_messages):
                if message.role == ChatMessageRole.USER and message.uploaded_asset is not None:
                    return message.uploaded_asset
        return None

    def _resolve_user_message_text(self, *, locale: str, message: str | None, asset: UploadedAsset | None) -> str:
        trimmed = (message or "").strip()
        if trimmed:
            return trimmed
        if asset is not None:
            return f"Фото вещи: {asset.original_filename}" if locale == "ru" else f"Item photo: {asset.original_filename}"
        return "Нужна рекомендация по образу" if locale == "ru" else "Need outfit guidance"

    def _should_skip_cooldown(self, *, context: ChatModeContext, requested_intent: ChatMode | None) -> bool:
        if requested_intent is not None:
            return True
        return context.active_mode != ChatMode.GENERAL_ADVICE and context.flow_state != FlowState.IDLE

    def _coerce_requested_intent(self, raw_value: str | None) -> ChatMode | None:
        if raw_value is None:
            return None
        try:
            return ChatMode(raw_value)
        except ValueError:
            return None

    def _flow_state_from_generation_status(self, status: GenerationStatus) -> FlowState:
        if status == GenerationStatus.PENDING:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED, GenerationStatus.RUNNING}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR

    def _fallback_empty_reply(self, locale: str) -> str:
        return "Продолжаем." if locale == "ru" else "Let's continue."

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
        return {"gender": gender, "height_cm": height_cm, "weight_kg": weight_kg}

    def _normalize_gender(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        lowered = value.strip().lower()
        if lowered in {"male", "man", "m", "м", "муж", "мужчина", "парень"}:
            return "male"
        if lowered in {"female", "woman", "f", "ж", "жен", "женщина", "девушка"}:
            return "female"
        return None

    def _extract_gender_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        if re.search(r"\b(мужчина|парень|male|man|guy)\b", lowered):
            return "male"
        if re.search(r"\b(женщина|девушка|female|woman|girl)\b", lowered):
            return "female"
        return None

    def _extract_height_cm(self, text: str) -> int | None:
        lowered = text.lower()
        named_match = re.search(r"(?:(?:рост)|height)\s*[:\-]?\s*(\d{2,3})", lowered)
        if named_match:
            return self._validate_height(int(named_match.group(1)))
        cm_match = re.search(r"\b(\d{3})\s*(?:см|cm)\b", lowered)
        if cm_match:
            return self._validate_height(int(cm_match.group(1)))
        meter_match = re.search(r"\b(1[.,]\d{2})\s*(?:м|m)\b", lowered)
        if meter_match:
            return self._validate_height(round(float(meter_match.group(1).replace(",", ".")) * 100))
        return None

    def _extract_weight_kg(self, text: str) -> int | None:
        lowered = text.lower()
        named_match = re.search(r"(?:(?:вес)|weight)\s*[:\-]?\s*(\d{2,3})", lowered)
        if named_match:
            return self._validate_weight(int(named_match.group(1)))
        kg_match = re.search(r"\b(\d{2,3})\s*(?:кг|kg)\b", lowered)
        if kg_match:
            return self._validate_weight(int(kg_match.group(1)))
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


stylist_service = StylistService()
