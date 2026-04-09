from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import StyleSourceRegistryEntry
from app.models.style_source_fetch_state import StyleSourceFetchState


MIN_WORKER_LEASE_SECONDS = 5.0


def _base_interval(source: StyleSourceRegistryEntry) -> float:
    min_delay = float(source.crawl_policy.min_delay_seconds)
    max_delay = float(source.crawl_policy.max_delay_seconds)
    if max_delay < min_delay:
        max_delay = min_delay
    return (min_delay + max_delay) / 2.0


class SourceFetchStateService:
    async def get_or_create(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
    ) -> StyleSourceFetchState:
        state = await self._load_state(session, source=source, create_if_missing=True)
        if state is None:
            raise ValueError(f"style_source_fetch_state for source {source.source_name!r} was not found")
        return state

    async def mark_success(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        http_status: int,
        at: datetime | None = None,
    ) -> StyleSourceFetchState:
        state = await self.get_or_create(session, source=source)
        now = at or datetime.now(UTC)
        base_interval = _base_interval(source)
        state.mode = "active"
        state.last_success_at = now
        state.last_http_status = http_status
        state.last_error_class = None
        state.consecutive_empty_bodies = 0
        state.current_min_interval_sec = base_interval
        state.next_allowed_at = now + timedelta(seconds=base_interval)
        return state

    async def mark_empty_body(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        http_status: int | None = None,
        at: datetime | None = None,
    ) -> StyleSourceFetchState:
        state = await self.get_or_create(session, source=source)
        now = at or datetime.now(UTC)
        new_empty_count = state.consecutive_empty_bodies + 1
        cooldown_seconds = random.uniform(
            float(source.crawl_policy.empty_body_cooldown_min_seconds),
            float(source.crawl_policy.empty_body_cooldown_max_seconds),
        )
        block_threshold = max(int(source.crawl_policy.blocked_after_consecutive_empty), 1)
        state.mode = "blocked_suspected" if new_empty_count >= block_threshold else "cooldown"
        state.last_empty_body_at = now
        state.last_http_status = http_status
        state.last_error_class = "empty_body"
        state.consecutive_empty_bodies = new_empty_count
        state.current_min_interval_sec = cooldown_seconds
        state.next_allowed_at = None if state.mode == "blocked_suspected" else now + timedelta(seconds=cooldown_seconds)
        return state

    async def mark_error(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        error_class: str,
        http_status: int | None = None,
        at: datetime | None = None,
    ) -> StyleSourceFetchState:
        state = await self.get_or_create(session, source=source)
        now = at or datetime.now(UTC)
        base_interval = _base_interval(source)
        backoff_seconds = max(float(source.crawl_policy.retry_backoff_seconds), base_interval)
        state.mode = "cooldown"
        state.last_http_status = http_status
        state.last_error_class = error_class
        state.current_min_interval_sec = backoff_seconds
        state.next_allowed_at = now + timedelta(seconds=backoff_seconds)
        return state

    async def try_acquire_worker_lease(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
        lease_ttl_seconds: float,
        now: datetime | None = None,
    ) -> tuple[bool, StyleSourceFetchState]:
        current_time = now or datetime.now(UTC)
        state = await self._load_state(session, source=source, for_update=True, create_if_missing=True)
        if state is None:
            raise ValueError(f"style_source_fetch_state for source {source.source_name!r} was not found")

        if self._has_conflicting_worker_lease(state, lease_owner=lease_owner, now=current_time):
            return False, state

        if state.worker_lease_owner != lease_owner:
            state.worker_lease_acquired_at = current_time
        state.worker_lease_owner = lease_owner
        state.worker_lease_heartbeat_at = current_time
        state.worker_lease_expires_at = self._lease_expires_at(now=current_time, lease_ttl_seconds=lease_ttl_seconds)
        session.add(state)
        await session.flush()
        return True, state

    async def refresh_worker_lease(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
        lease_ttl_seconds: float,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or datetime.now(UTC)
        state = await self._load_state(session, source=source, for_update=True, create_if_missing=False)
        if state is None:
            return False

        if self._has_conflicting_worker_lease(state, lease_owner=lease_owner, now=current_time):
            return False

        if state.worker_lease_owner != lease_owner:
            state.worker_lease_owner = lease_owner
            state.worker_lease_acquired_at = current_time
        state.worker_lease_heartbeat_at = current_time
        state.worker_lease_expires_at = self._lease_expires_at(now=current_time, lease_ttl_seconds=lease_ttl_seconds)
        session.add(state)
        await session.flush()
        return True

    async def release_worker_lease(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or datetime.now(UTC)
        state = await self._load_state(session, source=source, for_update=True, create_if_missing=False)
        if state is None:
            return False

        if self._has_conflicting_worker_lease(state, lease_owner=lease_owner, now=current_time):
            return False

        if (
            state.worker_lease_owner is None
            and state.worker_lease_acquired_at is None
            and state.worker_lease_heartbeat_at is None
            and state.worker_lease_expires_at is None
        ):
            return False

        state.worker_lease_owner = None
        state.worker_lease_acquired_at = None
        state.worker_lease_heartbeat_at = None
        state.worker_lease_expires_at = None
        session.add(state)
        await session.flush()
        return True

    async def _load_state(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        for_update: bool = False,
        create_if_missing: bool = True,
    ) -> StyleSourceFetchState | None:
        if create_if_missing:
            await self._ensure_state_row(session, source=source)

        query = select(StyleSourceFetchState).where(StyleSourceFetchState.source_name == source.source_name)
        if for_update:
            query = query.with_for_update()
        result = await session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def _ensure_state_row(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
    ) -> None:
        await session.execute(
            insert(StyleSourceFetchState)
            .values(
                source_name=source.source_name,
                mode="active",
                current_min_interval_sec=_base_interval(source),
            )
            .on_conflict_do_nothing(index_elements=[StyleSourceFetchState.source_name])
        )

    def _has_conflicting_worker_lease(
        self,
        state: StyleSourceFetchState,
        *,
        lease_owner: str,
        now: datetime,
    ) -> bool:
        if not self._worker_lease_is_active(state, now=now):
            return False
        return state.worker_lease_owner is not None and state.worker_lease_owner != lease_owner

    def _worker_lease_is_active(
        self,
        state: StyleSourceFetchState,
        *,
        now: datetime,
    ) -> bool:
        return bool(
            state.worker_lease_owner
            and state.worker_lease_expires_at is not None
            and state.worker_lease_expires_at > now
        )

    def _lease_expires_at(
        self,
        *,
        now: datetime,
        lease_ttl_seconds: float,
    ) -> datetime:
        ttl_seconds = max(float(lease_ttl_seconds), MIN_WORKER_LEASE_SECONDS)
        return now + timedelta(seconds=ttl_seconds)
