from pydantic import BaseModel, Field

from app.domain.stylist_runtime_settings import (
    MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
    MAX_DAILY_GENERATION_LIMIT_NON_ADMIN,
    MAX_MESSAGE_COOLDOWN_SECONDS,
    MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
)
from app.schemas.common import TimestampedRead


class StylistRuntimeSettingsUpdate(BaseModel):
    daily_generation_limit_non_admin: int = Field(ge=0, le=MAX_DAILY_GENERATION_LIMIT_NON_ADMIN)
    daily_chat_seconds_limit_non_admin: int = Field(ge=0, le=MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN)
    message_cooldown_seconds: int = Field(ge=0, le=MAX_MESSAGE_COOLDOWN_SECONDS)
    try_other_style_cooldown_seconds: int = Field(ge=0, le=MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS)


class StylistRuntimeSettingsRead(TimestampedRead):
    id: int
    daily_generation_limit_non_admin: int
    daily_chat_seconds_limit_non_admin: int
    message_cooldown_seconds: int
    try_other_style_cooldown_seconds: int
