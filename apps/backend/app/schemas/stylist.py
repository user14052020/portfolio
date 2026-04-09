from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ChatMessageRole
from app.schemas.common import TimestampedRead
from app.schemas.generation_job import GenerationJobRead
from app.schemas.upload import UploadedAssetRead


class StylistMessageRequest(BaseModel):
    session_id: str
    locale: str = "en"
    message: str | None = None
    uploaded_asset_id: int | None = None
    requested_intent: Literal["garment_matching", "style_exploration", "occasion_outfit"] | None = None
    profile_gender: str | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    auto_generate: bool = True


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
