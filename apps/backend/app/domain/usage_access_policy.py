from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


RequestedActionType = Literal["text_chat", "generation"]

USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT = "daily_generation_limit_reached"
USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT = "daily_chat_seconds_limit_reached"


@dataclass(frozen=True)
class UserContext:
    subject_id: str
    session_id: str | None = None
    user_id: int | None = None
    is_admin: bool = False


@dataclass(frozen=True)
class RequestedAction:
    action_type: RequestedActionType


@dataclass(frozen=True)
class UsageQuota:
    daily_generation_limit: int
    daily_chat_seconds_limit: int


@dataclass(frozen=True)
class UsageDecision:
    is_allowed: bool
    denial_reason: str | None
    remaining_generations: int
    remaining_chat_seconds: int


class UsageAccessPolicyService(Protocol):
    async def evaluate(
        self,
        session,
        *,
        subject: UserContext,
        action: RequestedAction,
    ) -> UsageDecision: ...
