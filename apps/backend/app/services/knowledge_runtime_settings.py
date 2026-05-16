from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.knowledge_runtime_settings import KnowledgeRuntimeSettings
from app.models import SiteSettings
from app.repositories.site_settings import SiteSettingsRepository, site_settings_repository


class KnowledgeRuntimeSettingsService:
    def __init__(self, repository: SiteSettingsRepository | None = None) -> None:
        self.repository = repository or site_settings_repository

    async def read_site_settings(self, session: AsyncSession) -> SiteSettings:
        return await self.repository.get_or_create_singleton(session)

    async def read(self, session: AsyncSession) -> KnowledgeRuntimeSettings:
        settings = await self.read_site_settings(session)
        return self._build_runtime_settings(settings)

    async def update(self, session: AsyncSession, *, payload: dict[str, object]) -> KnowledgeRuntimeSettings:
        site_settings = await self.read_site_settings(session)
        current = self._build_runtime_settings(site_settings)
        incoming = KnowledgeRuntimeSettings(**{**current.model_dump(), **payload})
        updated = await self.repository.update(
            session,
            site_settings,
            {
                "knowledge_runtime_flags_json": incoming.runtime_flags().model_dump(mode="json"),
                "knowledge_provider_priorities_json": incoming.normalized_provider_priorities(),
            },
        )
        return self._build_runtime_settings(updated)

    def _build_runtime_settings(self, settings: SiteSettings) -> KnowledgeRuntimeSettings:
        flags = dict(settings.knowledge_runtime_flags_json or {})
        priorities = dict(settings.knowledge_provider_priorities_json or {})
        return KnowledgeRuntimeSettings(
            style_ingestion_enabled=bool(flags.get("style_ingestion_enabled", True)),
            malevich_enabled=bool(flags.get("malevich_enabled", False)),
            fashion_historian_enabled=bool(flags.get("fashion_historian_enabled", False)),
            stylist_enabled=bool(flags.get("stylist_enabled", False)),
            use_editorial_knowledge=bool(flags.get("use_editorial_knowledge", False)),
            use_historical_context=bool(flags.get("use_historical_context", True)),
            use_color_poetics=bool(flags.get("use_color_poetics", True)),
            provider_priorities=priorities,
        )


class DatabaseKnowledgeRuntimeSettingsProvider:
    def __init__(
        self,
        *,
        session: AsyncSession,
        service: KnowledgeRuntimeSettingsService | None = None,
    ) -> None:
        self._session = session
        self._service = service or KnowledgeRuntimeSettingsService()

    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        settings = await self._service.read(self._session)
        return settings.runtime_flags()

    async def get_provider_priorities(self) -> dict[str, int]:
        settings = await self._service.read(self._session)
        return settings.normalized_provider_priorities()
