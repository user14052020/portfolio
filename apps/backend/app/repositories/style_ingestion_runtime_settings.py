from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StyleIngestionRuntimeSettings
from app.repositories.base import BaseRepository


class StyleIngestionRuntimeSettingsRepository(BaseRepository[StyleIngestionRuntimeSettings]):
    def __init__(self) -> None:
        super().__init__(StyleIngestionRuntimeSettings)

    async def get_by_source_name(
        self,
        session: AsyncSession,
        *,
        source_name: str,
    ) -> StyleIngestionRuntimeSettings | None:
        result = await session.execute(
            select(StyleIngestionRuntimeSettings)
            .where(StyleIngestionRuntimeSettings.source_name == source_name)
            .limit(1)
        )
        return result.scalar_one_or_none()


style_ingestion_runtime_settings_repository = StyleIngestionRuntimeSettingsRepository()
