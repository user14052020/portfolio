from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import SourceCrawlPolicy, StyleSourceRegistryEntry
from app.ingestion.styles.style_source_registry import AestheticsWikiSourceRegistry
from app.models import StyleIngestionRuntimeSettings
from app.repositories.style_ingestion_runtime_settings import style_ingestion_runtime_settings_repository


DEFAULT_WORKER_IDLE_SLEEP_SECONDS = 5.0
DEFAULT_WORKER_LEASE_TTL_SECONDS = 120.0
DEFAULT_WORKER_LEASE_HEARTBEAT_INTERVAL_SECONDS = 30.0


@dataclass(frozen=True)
class StyleIngestionRuntimeSettingsSnapshot:
    source_name: str
    min_delay_seconds: float
    max_delay_seconds: float
    jitter_ratio: float
    empty_body_cooldown_min_seconds: float
    empty_body_cooldown_max_seconds: float
    retry_backoff_seconds: float
    retry_backoff_jitter_seconds: float
    worker_idle_sleep_seconds: float
    worker_lease_ttl_seconds: float
    worker_lease_heartbeat_interval_seconds: float

    def apply_to_source(self, source: StyleSourceRegistryEntry) -> StyleSourceRegistryEntry:
        return replace(
            source,
            crawl_policy=replace(
                source.crawl_policy,
                min_delay_seconds=self.min_delay_seconds,
                max_delay_seconds=self.max_delay_seconds,
                jitter_ratio=self.jitter_ratio,
                empty_body_cooldown_min_seconds=self.empty_body_cooldown_min_seconds,
                empty_body_cooldown_max_seconds=self.empty_body_cooldown_max_seconds,
                retry_backoff_seconds=self.retry_backoff_seconds,
                retry_backoff_jitter_seconds=self.retry_backoff_jitter_seconds,
            ),
        )


@dataclass(frozen=True)
class ResolvedStyleIngestionSource:
    source: StyleSourceRegistryEntry
    runtime_settings: StyleIngestionRuntimeSettingsSnapshot


class StyleIngestionRuntimeSettingsService:
    def __init__(self, *, registry: AestheticsWikiSourceRegistry | None = None) -> None:
        self.registry = registry or AestheticsWikiSourceRegistry()
        self.repository = style_ingestion_runtime_settings_repository

    def build_default_snapshot(self, *, source_name: str) -> StyleIngestionRuntimeSettingsSnapshot:
        source = self.registry.get_source(source_name)
        policy = source.crawl_policy
        return StyleIngestionRuntimeSettingsSnapshot(
            source_name=source.source_name,
            min_delay_seconds=float(policy.min_delay_seconds),
            max_delay_seconds=float(policy.max_delay_seconds),
            jitter_ratio=float(policy.jitter_ratio),
            empty_body_cooldown_min_seconds=float(policy.empty_body_cooldown_min_seconds),
            empty_body_cooldown_max_seconds=float(policy.empty_body_cooldown_max_seconds),
            retry_backoff_seconds=float(policy.retry_backoff_seconds),
            retry_backoff_jitter_seconds=float(policy.retry_backoff_jitter_seconds),
            worker_idle_sleep_seconds=DEFAULT_WORKER_IDLE_SLEEP_SECONDS,
            worker_lease_ttl_seconds=DEFAULT_WORKER_LEASE_TTL_SECONDS,
            worker_lease_heartbeat_interval_seconds=DEFAULT_WORKER_LEASE_HEARTBEAT_INTERVAL_SECONDS,
        )

    def _snapshot_to_payload(self, snapshot: StyleIngestionRuntimeSettingsSnapshot) -> dict[str, Any]:
        return {
            "source_name": snapshot.source_name,
            "min_delay_seconds": snapshot.min_delay_seconds,
            "max_delay_seconds": snapshot.max_delay_seconds,
            "jitter_ratio": snapshot.jitter_ratio,
            "empty_body_cooldown_min_seconds": snapshot.empty_body_cooldown_min_seconds,
            "empty_body_cooldown_max_seconds": snapshot.empty_body_cooldown_max_seconds,
            "retry_backoff_seconds": snapshot.retry_backoff_seconds,
            "retry_backoff_jitter_seconds": snapshot.retry_backoff_jitter_seconds,
            "worker_idle_sleep_seconds": snapshot.worker_idle_sleep_seconds,
            "worker_lease_ttl_seconds": snapshot.worker_lease_ttl_seconds,
            "worker_lease_heartbeat_interval_seconds": snapshot.worker_lease_heartbeat_interval_seconds,
        }

    def _model_to_snapshot(
        self,
        model: StyleIngestionRuntimeSettings,
    ) -> StyleIngestionRuntimeSettingsSnapshot:
        return StyleIngestionRuntimeSettingsSnapshot(
            source_name=model.source_name,
            min_delay_seconds=float(model.min_delay_seconds),
            max_delay_seconds=float(model.max_delay_seconds),
            jitter_ratio=float(model.jitter_ratio),
            empty_body_cooldown_min_seconds=float(model.empty_body_cooldown_min_seconds),
            empty_body_cooldown_max_seconds=float(model.empty_body_cooldown_max_seconds),
            retry_backoff_seconds=float(model.retry_backoff_seconds),
            retry_backoff_jitter_seconds=float(model.retry_backoff_jitter_seconds),
            worker_idle_sleep_seconds=float(model.worker_idle_sleep_seconds),
            worker_lease_ttl_seconds=float(model.worker_lease_ttl_seconds),
            worker_lease_heartbeat_interval_seconds=float(model.worker_lease_heartbeat_interval_seconds),
        )

    async def get_or_create(
        self,
        session: AsyncSession,
        *,
        source_name: str,
    ) -> StyleIngestionRuntimeSettings:
        self.registry.get_source(source_name)
        settings = await self.repository.get_by_source_name(session, source_name=source_name)
        if settings is not None:
            return settings
        default_snapshot = self.build_default_snapshot(source_name=source_name)
        return await self.repository.create(session, self._snapshot_to_payload(default_snapshot))

    async def read(
        self,
        session: AsyncSession,
        *,
        source_name: str,
    ) -> StyleIngestionRuntimeSettings:
        return await self.get_or_create(session, source_name=source_name)

    async def update(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        payload: dict[str, Any],
    ) -> StyleIngestionRuntimeSettings:
        settings = await self.get_or_create(session, source_name=source_name)
        update_payload = {
            "source_name": source_name,
            **payload,
        }
        return await self.repository.update(session, settings, update_payload)

    async def read_snapshot(
        self,
        session: AsyncSession,
        *,
        source_name: str,
    ) -> StyleIngestionRuntimeSettingsSnapshot:
        settings = await self.get_or_create(session, source_name=source_name)
        return self._model_to_snapshot(settings)

    async def resolve_source(
        self,
        session: AsyncSession,
        *,
        source_name: str,
    ) -> ResolvedStyleIngestionSource:
        base_source = self.registry.get_source(source_name)
        snapshot = await self.read_snapshot(session, source_name=source_name)
        return ResolvedStyleIngestionSource(
            source=snapshot.apply_to_source(base_source),
            runtime_settings=snapshot,
        )
