from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.application.stylist_chat.results.decision_result import DecisionResult
from app.domain.chat_context import ChatModeContext
from app.models.enums import ChatMessageRole
from app.schemas.common import TimestampedRead
from app.schemas.generation_job import GenerationJobRead
from app.schemas.upload import UploadedAssetRead


class StylistMessageRequest(BaseModel):
    session_id: str
    locale: str = "en"
    message: str | None = None
    asset_id: int | None = None
    uploaded_asset_id: int | None = None
    requested_intent: Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"] | None = None
    command_name: str | None = None
    command_step: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_message_id: str | None = None
    command_id: str | None = None
    correlation_id: str | None = None
    profile_gender: str | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    auto_generate: bool = True

    @model_validator(mode="after")
    def sync_asset_ids(self) -> "StylistMessageRequest":
        if self.uploaded_asset_id is None and self.asset_id is not None:
            self.uploaded_asset_id = self.asset_id
        if self.asset_id is None and self.uploaded_asset_id is not None:
            self.asset_id = self.uploaded_asset_id
        if self.client_message_id is None:
            raw_value = self.metadata.get("clientMessageId") or self.metadata.get("client_message_id")
            if isinstance(raw_value, str):
                self.client_message_id = raw_value.strip() or None
        if self.command_id is None:
            raw_value = self.metadata.get("commandId") or self.metadata.get("command_id")
            if isinstance(raw_value, str):
                self.command_id = raw_value.strip() or None
        if self.command_id is None:
            self.command_id = self.client_message_id
        if self.correlation_id is None:
            raw_value = self.metadata.get("correlationId") or self.metadata.get("correlation_id")
            if isinstance(raw_value, str):
                self.correlation_id = raw_value.strip() or None
        if self.correlation_id is None:
            self.correlation_id = self.command_id
        return self


class ChatMessageRead(TimestampedRead):
    id: int
    session_id: str
    role: ChatMessageRole
    locale: str
    content: str
    generation_job_id: int | None = None
    generation_job: GenerationJobRead | None = None
    uploaded_asset: UploadedAssetRead | None = None
    payload: dict


class ChatHistoryPageRead(BaseModel):
    items: list[ChatMessageRead]
    has_more: bool
    next_before_message_id: int | None = None


class StylistMessageResponse(BaseModel):
    session_id: str
    recommendation_text: str
    prompt: str
    assistant_message: ChatMessageRead
    generation_job: GenerationJobRead | None = None
    timestamp: datetime
    decision: DecisionResult
    session_context: ChatModeContext
