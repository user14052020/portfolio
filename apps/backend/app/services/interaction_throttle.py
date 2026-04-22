from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interaction_throttle import (
    THROTTLE_ACTION_MESSAGE,
    THROTTLE_ACTION_TRY_OTHER_STYLE,
    ThrottleActionType,
    ThrottleDecision,
)
from app.models import ChatMessage
from app.models.enums import ChatMessageRole
from app.services.stylist_runtime_settings import StylistRuntimeSettingsService


class InteractionThrottleService:
    def __init__(self, *, runtime_settings_service: StylistRuntimeSettingsService | None = None) -> None:
        self.runtime_settings_service = runtime_settings_service or StylistRuntimeSettingsService()

    async def can_submit(
        self,
        session: AsyncSession,
        *,
        subject_id: str,
        action_type: ThrottleActionType,
    ) -> ThrottleDecision:
        blocking_decisions = await self._active_blocking_decisions(
            session,
            subject_id=subject_id,
        )
        if not blocking_decisions:
            return ThrottleDecision(
                is_allowed=True,
                action_type=action_type,
                retry_after_seconds=0,
                next_allowed_at=None,
                cooldown_seconds=0,
            )
        return max(blocking_decisions, key=lambda item: item.retry_after_seconds)

    async def _resolve_cooldown_seconds(
        self,
        session: AsyncSession,
        *,
        action_type: ThrottleActionType,
    ) -> int:
        limits = await self.runtime_settings_service.get_limits(session)
        if action_type == THROTTLE_ACTION_TRY_OTHER_STYLE:
            return max(int(limits.try_other_style_cooldown_seconds), 0)
        return max(int(limits.message_cooldown_seconds), 0)

    async def _get_latest_submission_time(
        self,
        session: AsyncSession,
        *,
        subject_id: str,
        action_type: ThrottleActionType,
    ) -> datetime | None:
        subject_path = ChatMessage.payload["usage_subject_id"].as_string()
        action_path = ChatMessage.payload["throttle_action_type"].as_string()
        statement = (
            select(ChatMessage.created_at)
            .where(
                and_(
                    ChatMessage.role == ChatMessageRole.USER,
                    subject_path == subject_id,
                    action_path == action_type,
                )
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def _active_blocking_decisions(
        self,
        session: AsyncSession,
        *,
        subject_id: str,
    ) -> list[ThrottleDecision]:
        decisions: list[ThrottleDecision] = []
        for action_type in (THROTTLE_ACTION_MESSAGE, THROTTLE_ACTION_TRY_OTHER_STYLE):
            cooldown_seconds = await self._resolve_cooldown_seconds(session, action_type=action_type)
            if cooldown_seconds <= 0:
                continue
            latest_submitted_at = await self._get_latest_submission_time(
                session,
                subject_id=subject_id,
                action_type=action_type,
            )
            if latest_submitted_at is None:
                continue
            next_allowed_at = latest_submitted_at + timedelta(seconds=cooldown_seconds)
            retry_after_seconds = max(0, int(math.ceil((next_allowed_at - datetime.now(timezone.utc)).total_seconds())))
            if retry_after_seconds <= 0:
                continue
            decisions.append(
                ThrottleDecision(
                    is_allowed=False,
                    action_type=action_type,
                    retry_after_seconds=retry_after_seconds,
                    next_allowed_at=next_allowed_at,
                    cooldown_seconds=cooldown_seconds,
                )
            )
        return decisions
