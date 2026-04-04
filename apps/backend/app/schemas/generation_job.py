from datetime import datetime

from pydantic import BaseModel

from app.models.enums import GenerationProvider, GenerationStatus
from app.schemas.common import TimestampedRead
from app.schemas.upload import UploadedAssetRead


class GenerationJobCreate(BaseModel):
    session_id: str | None = None
    input_text: str | None = None
    recommendation_ru: str
    recommendation_en: str
    prompt: str
    input_asset_id: int | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    provider: GenerationProvider = GenerationProvider.COMFYUI


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
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    error_message: str | None = None
    provider_payload: dict
    started_at: datetime | None = None
    completed_at: datetime | None = None

