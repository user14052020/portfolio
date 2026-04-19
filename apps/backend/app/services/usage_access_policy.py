from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.usage_access_policy import (
    USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT,
    USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
    RequestedAction,
    UsageDecision,
    UsageQuota,
    UserContext,
)
from app.models import ChatMessage, GenerationJob, User
from app.models.enums import ChatMessageRole, RoleCode
from app.services.stylist_runtime_settings import StylistRuntimeSettingsService


UTC = timezone.utc
WORDS_PER_SECOND_READING_ESTIMATE = 2.5


class UsageAccessPolicyService:
    def __init__(self, *, runtime_settings_service: StylistRuntimeSettingsService | None = None) -> None:
        self.runtime_settings_service = runtime_settings_service or StylistRuntimeSettingsService()

    def build_subject(
        self,
        *,
        current_user: User | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trusted_metadata: bool = False,
    ) -> UserContext:
        metadata = metadata if isinstance(metadata, dict) else {}
        raw_subject_id = metadata.get("usage_subject_id")
        raw_session_id = metadata.get("usage_session_id")
        raw_user_id = metadata.get("usage_user_id")
        raw_is_admin = metadata.get("usage_is_admin")

        if trusted_metadata and isinstance(raw_subject_id, str) and raw_subject_id.strip():
            return UserContext(
                subject_id=raw_subject_id.strip(),
                session_id=self._optional_text(raw_session_id) or session_id,
                user_id=self._coerce_int(raw_user_id),
                is_admin=self._coerce_bool(raw_is_admin),
            )

        if current_user is not None:
            is_admin = current_user.role.name == RoleCode.ADMIN.value
            return UserContext(
                subject_id=f"user:{current_user.id}",
                session_id=session_id,
                user_id=current_user.id,
                is_admin=is_admin,
            )

        cleaned_session_id = self._optional_text(session_id)
        if cleaned_session_id is None:
            raise ValueError("Anonymous runtime requests must include session_id for usage policy evaluation.")
        return UserContext(
            subject_id=f"session:{cleaned_session_id}",
            session_id=cleaned_session_id,
            user_id=None,
            is_admin=False,
        )

    def subject_to_metadata(self, subject: UserContext) -> dict[str, Any]:
        return {
            "usage_subject_id": subject.subject_id,
            "usage_session_id": subject.session_id,
            "usage_user_id": subject.user_id,
            "usage_is_admin": subject.is_admin,
        }

    async def evaluate(
        self,
        session: AsyncSession,
        *,
        subject: UserContext,
        action: RequestedAction,
    ) -> UsageDecision:
        limits = await self.runtime_settings_service.get_limits(session)
        quota = UsageQuota(
            daily_generation_limit=max(int(limits.daily_generation_limit_non_admin), 0),
            daily_chat_seconds_limit=max(int(limits.daily_chat_seconds_limit_non_admin), 0),
        )
        generation_usage = await self._count_generation_jobs_today(session, subject=subject)
        chat_seconds_usage = await self._sum_text_chat_seconds_today(session, subject=subject)

        remaining_generations = max(quota.daily_generation_limit - generation_usage, 0)
        remaining_chat_seconds = max(quota.daily_chat_seconds_limit - chat_seconds_usage, 0)

        if subject.is_admin:
            return UsageDecision(
                is_allowed=True,
                denial_reason=None,
                remaining_generations=remaining_generations,
                remaining_chat_seconds=remaining_chat_seconds,
            )

        if action.action_type == "generation" and generation_usage >= quota.daily_generation_limit:
            return UsageDecision(
                is_allowed=False,
                denial_reason=USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
                remaining_generations=0,
                remaining_chat_seconds=remaining_chat_seconds,
            )

        if action.action_type == "text_chat" and chat_seconds_usage >= quota.daily_chat_seconds_limit:
            return UsageDecision(
                is_allowed=False,
                denial_reason=USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT,
                remaining_generations=remaining_generations,
                remaining_chat_seconds=0,
            )

        return UsageDecision(
            is_allowed=True,
            denial_reason=None,
            remaining_generations=remaining_generations,
            remaining_chat_seconds=remaining_chat_seconds,
        )

    async def _count_generation_jobs_today(self, session: AsyncSession, *, subject: UserContext) -> int:
        day_start, day_end = self._current_day_bounds()
        subject_path = GenerationJob.provider_payload["_stylist"]["usage_subject_id"].as_string()
        count_query = select(func.count()).select_from(GenerationJob).where(
            and_(
                subject_path == subject.subject_id,
                GenerationJob.created_at >= day_start,
                GenerationJob.created_at < day_end,
                GenerationJob.deleted_at.is_(None),
            )
        )
        result = await session.execute(count_query)
        return int(result.scalar_one() or 0)

    async def _sum_text_chat_seconds_today(self, session: AsyncSession, *, subject: UserContext) -> int:
        day_start, day_end = self._current_day_bounds()
        subject_path = ChatMessage.payload["usage_subject_id"].as_string()
        statement = select(ChatMessage.content).where(
            and_(
                ChatMessage.role == ChatMessageRole.ASSISTANT,
                ChatMessage.generation_job_id.is_(None),
                subject_path == subject.subject_id,
                ChatMessage.created_at >= day_start,
                ChatMessage.created_at < day_end,
            )
        )
        result = await session.execute(statement)
        return sum(self._estimate_text_chat_seconds(content) for content in result.scalars().all())

    # We do not store wall-clock session duration, so "chat seconds" are approximated
    # as assistant text reading time to keep the quota deterministic and DB-backed.
    def _estimate_text_chat_seconds(self, content: str | None) -> int:
        if content is None:
            return 0
        words = re.findall(r"\w+", content, flags=re.UNICODE)
        if not words:
            return 1 if str(content).strip() else 0
        return max(int(math.ceil(len(words) / WORDS_PER_SECOND_READING_ESTIMATE)), 1)

    def _current_day_bounds(self) -> tuple[datetime, datetime]:
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start, day_start + timedelta(days=1)

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _coerce_int(self, value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def _coerce_bool(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
