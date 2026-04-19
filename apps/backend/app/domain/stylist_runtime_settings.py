from __future__ import annotations

from dataclasses import dataclass


DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN = 5
DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN = 600
DEFAULT_MESSAGE_COOLDOWN_SECONDS = 60
DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS = 60

MAX_DAILY_GENERATION_LIMIT_NON_ADMIN = 1000
MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN = 86_400
MAX_MESSAGE_COOLDOWN_SECONDS = 3_600
MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS = 3_600


@dataclass(frozen=True)
class StylistRuntimeLimits:
    daily_generation_limit_non_admin: int
    daily_chat_seconds_limit_non_admin: int
    message_cooldown_seconds: int
    try_other_style_cooldown_seconds: int
