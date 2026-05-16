from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.reasoning import VoiceRuntimeFlags
from app.domain.voice_runtime_settings import VoiceRuntimeSettings
from app.models import SiteSettings
from app.repositories.site_settings import SiteSettingsRepository, site_settings_repository


class VoiceRuntimeSettingsService:
    def __init__(self, repository: SiteSettingsRepository | None = None) -> None:
        self.repository = repository or site_settings_repository

    async def read_site_settings(self, session: AsyncSession) -> SiteSettings:
        return await self.repository.get_or_create_singleton(session)

    async def read(self, session: AsyncSession) -> VoiceRuntimeSettings:
        settings = await self.read_site_settings(session)
        return self._build_runtime_settings(settings)

    async def update(self, session: AsyncSession, *, payload: dict[str, object]) -> VoiceRuntimeSettings:
        site_settings = await self.read_site_settings(session)
        current = self._build_runtime_settings(site_settings)
        incoming = VoiceRuntimeSettings(**{**current.model_dump(), **payload})
        updated = await self.repository.update(
            session,
            site_settings,
            {
                "voice_runtime_flags_json": incoming.runtime_flags().model_dump(mode="json"),
            },
        )
        return self._build_runtime_settings(updated)

    def _build_runtime_settings(self, settings: SiteSettings) -> VoiceRuntimeSettings:
        flags = dict(settings.voice_runtime_flags_json or {})
        return VoiceRuntimeSettings(
            historian_enabled=bool(flags.get("historian_enabled", True)),
            color_poetics_enabled=bool(flags.get("color_poetics_enabled", True)),
            deep_mode_enabled=bool(flags.get("deep_mode_enabled", True)),
            cta_experimental_copy_enabled=bool(flags.get("cta_experimental_copy_enabled", False)),
        )


class DatabaseVoiceRuntimeSettingsProvider:
    def __init__(
        self,
        *,
        session: AsyncSession,
        service: VoiceRuntimeSettingsService | None = None,
    ) -> None:
        self._session = session
        self._service = service or VoiceRuntimeSettingsService()

    async def get_runtime_flags(self) -> VoiceRuntimeFlags:
        settings = await self._service.read(self._session)
        return settings.runtime_flags()
