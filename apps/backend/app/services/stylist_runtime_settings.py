from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.stylist_runtime_settings import StylistRuntimeLimits
from app.models import SiteSettings
from app.repositories.site_settings import SiteSettingsRepository, site_settings_repository


class StylistRuntimeSettingsService:
    def __init__(self, repository: SiteSettingsRepository | None = None) -> None:
        self.repository = repository or site_settings_repository

    async def read(self, session: AsyncSession) -> SiteSettings:
        return await self.repository.get_or_create_singleton(session)

    async def update(self, session: AsyncSession, *, payload: dict[str, int]) -> SiteSettings:
        settings = await self.read(session)
        return await self.repository.update(session, settings, payload)

    async def get_limits(self, session: AsyncSession) -> StylistRuntimeLimits:
        settings = await self.read(session)
        return StylistRuntimeLimits(
            daily_generation_limit_non_admin=int(settings.daily_generation_limit_non_admin),
            daily_chat_seconds_limit_non_admin=int(settings.daily_chat_seconds_limit_non_admin),
            message_cooldown_seconds=int(settings.message_cooldown_seconds),
            try_other_style_cooldown_seconds=int(settings.try_other_style_cooldown_seconds),
        )
