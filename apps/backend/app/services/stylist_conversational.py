import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.models import UploadedAsset
from app.models.chat_message import ChatMessage
from app.models.enums import ChatMessageRole
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.uploads import uploads_repository
from app.schemas.stylist import StylistMessageRequest
from app.services.chat_context_store import chat_context_store
from app.services.generation import generation_service
from app.services.stylist_orchestrator import build_stylist_chat_orchestrator


class StylistService:
    async def process_message(self, session: AsyncSession, payload: StylistMessageRequest):
        locale = "ru" if payload.locale == "ru" else "en"
        session_state_record, context = await chat_context_store.load(session, payload.session_id)
        context = await self._sync_context_generation_state(session, context)
        requested_intent = self._coerce_requested_intent(payload.requested_intent)
        resolved_client_message_id = payload.client_message_id
        if resolved_client_message_id is None:
            raw_value = payload.metadata.get("clientMessageId") or payload.metadata.get("client_message_id")
            if isinstance(raw_value, str):
                resolved_client_message_id = raw_value.strip() or None
        resolved_command_id = payload.command_id or resolved_client_message_id
        resolved_correlation_id = payload.correlation_id or resolved_command_id

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
                    "client_message_id": resolved_client_message_id,
                    "command_id": resolved_command_id,
                    "correlation_id": resolved_correlation_id,
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
        command = ChatCommand(
            session_id=payload.session_id,
            locale=locale,
            message=user_message_text,
            requested_intent=requested_intent,
            command_name=payload.command_name,
            command_step=payload.command_step,
            asset_id=payload.asset_id or payload.uploaded_asset_id,
            metadata=payload.metadata,
            client_message_id=resolved_client_message_id,
            command_id=resolved_command_id,
            correlation_id=resolved_correlation_id,
            user_message_id=user_message.id,
            profile_context=profile_context,
            asset_metadata=self._serialize_asset_metadata(asset),
            fallback_history=self._serialize_message_history(recent_messages),
        )
        orchestrator = build_stylist_chat_orchestrator(session)
        decision = await orchestrator.handle(command=command)
        session_state_record, context = await chat_context_store.load(session, payload.session_id)
        generation_job = None
        if decision.job_id:
            generation_job = await generation_jobs_repository.get_by_public_id(session, decision.job_id)
            if generation_job is not None:
                generation_job = await generation_service.enrich_job_runtime(session, generation_job)

        assistant_text = decision.text_reply or self._fallback_empty_reply(locale)
        assistant_payload = {
            "decision_type": decision.decision_type.value,
            "active_mode": context.active_mode.value,
            "flow_state": context.flow_state.value,
            "clarification_kind": context.clarification_kind.value if context.clarification_kind else None,
            "prompt": decision.generation_payload.prompt if decision.generation_payload else "",
            "image_brief_en": decision.generation_payload.image_brief_en if decision.generation_payload else "",
            "context_patch": decision.context_patch,
            "telemetry": decision.telemetry,
            "kind": decision.decision_type.value,
            "command_name": payload.command_name,
            "command_step": payload.command_step,
            "client_message_id": resolved_client_message_id,
            "command_id": resolved_command_id,
            "correlation_id": resolved_correlation_id,
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

    def _serialize_asset_metadata(self, asset: UploadedAsset | None) -> dict[str, Any]:
        if asset is None:
            return {}
        asset_type = getattr(asset.asset_type, "value", asset.asset_type)
        return {
            "asset_id": asset.id,
            "original_filename": asset.original_filename,
            "mime_type": asset.mime_type,
            "size_bytes": asset.size_bytes,
            "asset_type": asset_type,
        }

    def _serialize_message_history(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for message in messages:
            content = (message.content or "").strip()
            if not content:
                continue
            role_value = getattr(message.role, "value", "user")
            if role_value not in {"user", "assistant", "system"}:
                role_value = "user"
            history.append({"role": role_value, "content": content[:280]})
        return history

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

    async def _sync_context_generation_state(self, session: AsyncSession, context: ChatModeContext) -> ChatModeContext:
        orchestrator = build_stylist_chat_orchestrator(session)
        return await orchestrator.generation_scheduler.sync_context(context)

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
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
            FlowState.READY_FOR_DECISION,
            FlowState.READY_FOR_GENERATION,
            FlowState.GENERATION_QUEUED,
            FlowState.GENERATION_IN_PROGRESS,
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
