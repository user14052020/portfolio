from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, GenerationJob, UploadedAsset
from app.repositories.base import BaseRepository


class UploadsRepository(BaseRepository[UploadedAsset]):
    def __init__(self) -> None:
        super().__init__(UploadedAsset)

    async def list_older_than(self, session: AsyncSession, cutoff: datetime) -> list[UploadedAsset]:
        chat_asset_ids = select(ChatMessage.uploaded_asset_id).where(ChatMessage.uploaded_asset_id.is_not(None))
        generation_input_asset_ids = select(GenerationJob.input_asset_id).where(GenerationJob.input_asset_id.is_not(None))
        result = await session.execute(
            select(UploadedAsset).where(
                UploadedAsset.created_at < cutoff,
                or_(
                    UploadedAsset.related_entity == "generation_input",
                    UploadedAsset.id.in_(chat_asset_ids),
                    UploadedAsset.id.in_(generation_input_asset_ids),
                ),
            )
        )
        return list(result.scalars().all())

    async def delete_by_ids(self, session: AsyncSession, asset_ids: list[int]) -> int:
        if not asset_ids:
            return 0
        result = await session.execute(delete(UploadedAsset).where(UploadedAsset.id.in_(asset_ids)))
        await session.flush()
        return int(result.rowcount or 0)


uploads_repository = UploadsRepository()
