from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SiteSettings
from app.repositories.base import BaseRepository


class SiteSettingsRepository(BaseRepository[SiteSettings]):
    def __init__(self) -> None:
        super().__init__(SiteSettings)

    async def get_singleton(self, session: AsyncSession) -> SiteSettings | None:
        result = await session.execute(select(SiteSettings).limit(1))
        return result.scalar_one_or_none()


site_settings_repository = SiteSettingsRepository()

