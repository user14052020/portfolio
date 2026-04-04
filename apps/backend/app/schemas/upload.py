from pydantic import BaseModel

from app.models.enums import AssetType
from app.schemas.common import TimestampedRead


class UploadedAssetRead(TimestampedRead):
    id: int
    original_filename: str
    storage_path: str
    public_url: str
    mime_type: str
    size_bytes: int
    asset_type: AssetType
    storage_backend: str
    related_entity: str | None = None
    related_entity_id: int | None = None


class UploadResponse(BaseModel):
    asset: UploadedAssetRead

