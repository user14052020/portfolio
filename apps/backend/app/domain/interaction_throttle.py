from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


ThrottleActionType = Literal["message", "try_other_style"]

THROTTLE_ACTION_MESSAGE: ThrottleActionType = "message"
THROTTLE_ACTION_TRY_OTHER_STYLE: ThrottleActionType = "try_other_style"


@dataclass(frozen=True)
class ThrottleDecision:
    is_allowed: bool
    action_type: ThrottleActionType
    retry_after_seconds: int
    next_allowed_at: datetime | None
    cooldown_seconds: int


class InteractionThrottleService(Protocol):
    async def can_submit(
        self,
        session,
        *,
        subject_id: str,
        action_type: ThrottleActionType,
    ) -> ThrottleDecision: ...
