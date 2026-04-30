from hashlib import sha1
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.domain.chat_modes import ChatMode


class ChatCommand(BaseModel):
    session_id: str
    locale: str = "en"
    message: str | None = None
    requested_intent: ChatMode | None = None
    command_name: str | None = None
    command_step: str | None = None
    asset_id: int | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    client_message_id: str | None = None
    command_id: str | None = None
    correlation_id: str | None = None
    user_message_id: int | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)
    asset_metadata: dict[str, Any] = Field(default_factory=dict)
    fallback_history: list[dict[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_identifiers(self) -> "ChatCommand":
        if self.client_message_id is None:
            raw_value = self.metadata.get("clientMessageId") or self.metadata.get("client_message_id")
            if isinstance(raw_value, str):
                cleaned = raw_value.strip()
                self.client_message_id = cleaned or None
        if self.command_id is None:
            raw_value = self.metadata.get("commandId") or self.metadata.get("command_id")
            if isinstance(raw_value, str):
                cleaned = raw_value.strip()
                self.command_id = cleaned or None
        if self.command_id is None and self.client_message_id is not None:
            self.command_id = self.client_message_id
        if self.command_id is None and self.user_message_id is not None:
            self.command_id = f"msg-{self.user_message_id}"
        if self.correlation_id is None:
            raw_value = self.metadata.get("correlationId") or self.metadata.get("correlation_id")
            if isinstance(raw_value, str):
                cleaned = raw_value.strip()
                self.correlation_id = cleaned or None
        if self.correlation_id is None:
            self.correlation_id = self.command_id
        return self

    @property
    def source(self) -> str | None:
        raw_value = self.metadata.get("source")
        if isinstance(raw_value, str):
            cleaned = raw_value.strip()
            return cleaned or None
        return None

    def normalized_message(self) -> str:
        return (self.message or "").strip()

    def build_generation_idempotency_key(self, *, active_mode: ChatMode) -> str:
        if self.command_id:
            return f"{self.session_id}:{active_mode.value}:cmd:{self.command_id}"
        if self.client_message_id:
            return f"{self.session_id}:{active_mode.value}:{self.client_message_id}"
        if self.user_message_id is not None:
            return f"{self.session_id}:{active_mode.value}:msg:{self.user_message_id}"
        seed = "|".join(
            [
                self.session_id,
                active_mode.value,
                self.command_name or "",
                self.command_step or "",
                self.normalized_message()[:160],
                str(self.asset_id or ""),
            ]
        )
        return f"{self.session_id}:{active_mode.value}:{sha1(seed.encode('utf-8')).hexdigest()[:16]}"
