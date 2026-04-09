from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.domain.chat_context import ChatModeContext
from app.domain.decision_result import DecisionResult
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
