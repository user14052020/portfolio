from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import GenerationProvider, GenerationStatus
from app.schemas.common import ORMModel, TimestampedRead
from app.schemas.upload import UploadedAssetRead


class GenerationJobCreate(BaseModel):
    session_id: str | None = None
    input_text: str | None = None
    recommendation_ru: str
    recommendation_en: str
    prompt: str
    negative_prompt: str | None = None
    input_asset_id: int | None = None
    client_ip: str | None = None
    client_user_agent: str | None = None
    request_origin: str | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    workflow_name: str | None = None
    workflow_version: str | None = None
    visual_generation_plan: dict | None = None
    generation_metadata: dict | None = None
    metadata: dict = Field(default_factory=dict)
    idempotency_key: str | None = None
    provider: GenerationProvider = GenerationProvider.COMFYUI


class StyleExplanationRead(ORMModel):
    style_id: str | None = None
    style_name: str | None = None
    short_explanation: str | None = None
    supporting_text: str | None = None
    distinct_points: list[str] = Field(default_factory=list)


class GenerationJobRead(TimestampedRead):
    id: int
    public_id: str
    session_id: str | None = None
    provider: GenerationProvider
    status: GenerationStatus
    input_text: str | None = None
    prompt: str
    recommendation_ru: str
    recommendation_en: str
    input_asset: UploadedAssetRead | None = None
    result_url: str | None = None
    external_job_id: str | None = None
    progress: int
    client_ip: str | None = None
    client_user_agent: str | None = None
    request_origin: str | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    error_message: str | None = None
    provider_payload: dict
    operation_log: list[dict]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deleted_at: datetime | None = None
    queue_position: int | None = None
    queue_ahead: int | None = None
    queue_total: int | None = None
    queue_refresh_available_at: datetime | None = None
    queue_refresh_retry_after_seconds: int | None = None
    visual_generation_plan: dict | None = None
    generation_metadata: dict | None = None
    style_explanation: StyleExplanationRead | None = None
