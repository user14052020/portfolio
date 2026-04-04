from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import AssetType
from app.repositories.uploads import uploads_repository


class UploadService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def save_upload(
        self,
        session: AsyncSession,
        file: UploadFile,
        *,
        related_entity: str | None = None,
        related_entity_id: int | None = None,
        uploaded_by_id: int | None = None,
    ):
        content = await file.read()
        suffix = Path(file.filename or "upload.bin").suffix or ".bin"
        target_dir = self.settings.media_root / "uploads" / uuid4().hex[:2]
        target_dir.mkdir(parents=True, exist_ok=True)
        storage_name = f"{uuid4().hex}{suffix}"
        storage_path = target_dir / storage_name
        storage_path.write_bytes(content)
        relative_path = storage_path.relative_to(self.settings.media_root)
        public_url = f"{self.settings.media_url}/{relative_path.as_posix()}"

        asset_type = self._detect_asset_type(file.content_type or "", suffix)
        asset = await uploads_repository.create(
            session,
            {
                "original_filename": file.filename or storage_name,
                "storage_path": str(relative_path),
                "public_url": public_url,
                "mime_type": file.content_type or "application/octet-stream",
                "size_bytes": len(content),
                "asset_type": asset_type,
                "storage_backend": "local",
                "uploaded_by_id": uploaded_by_id,
                "related_entity": related_entity,
                "related_entity_id": related_entity_id,
            },
        )
        return asset

    def _detect_asset_type(self, content_type: str, suffix: str) -> AssetType:
        lowered = content_type.lower()
        if lowered.startswith("image/"):
            return AssetType.IMAGE
        if lowered.startswith("video/"):
            return AssetType.VIDEO
        if suffix.lower() in {".glb", ".gltf", ".usdz"}:
            return AssetType.MODEL3D
        return AssetType.DOCUMENT


upload_service = UploadService()

