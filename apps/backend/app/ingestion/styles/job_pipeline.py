from __future__ import annotations

import asyncio
from contextlib import suppress
import hashlib
import os
import socket
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify

from app.db.session import SessionLocal
from app.ingestion.styles.batch_runner import StyleBatchIngestionRunner
from app.ingestion.styles.contracts import (
    CandidateRemoteState,
    DiscoveredStyleCandidate,
    IngestWorkerRunReport,
    ProcessedIngestJobResult,
    QueuedJobBatchReport,
    ScrapedStylePage,
    StyleSourceRegistryEntry,
)
from app.ingestion.styles.ingest_job_service import (
    COOLDOWN_DEFERRED_STATUS,
    HARD_FAILED_STATUS,
    SOFT_FAILED_STATUS,
    StyleIngestJobService,
)
from app.ingestion.styles.source_fetch_state_service import SourceFetchStateService
from app.ingestion.styles.style_db_writer import SQLAlchemyStyleDBWriter, build_style_persistence_payload
from app.ingestion.styles.style_enricher import DefaultStyleEnricher
from app.ingestion.styles.style_normalizer import DefaultStyleNormalizer
from app.ingestion.styles.style_scraper import HTTPStyleScraper
from app.ingestion.styles.style_source_registry import AestheticsWikiSourceRegistry
from app.ingestion.styles.style_validator import DefaultStyleValidator
from app.models.style_ingest_attempt import StyleIngestAttempt
from app.models.style_ingest_job import StyleIngestJob
from app.models.style_source_page import StyleSourcePage
from app.models.style_source_page_version import StyleSourcePageVersion


DISCOVER_SOURCE_PAGES_JOB_TYPE = "discover_source_pages"
FETCH_STYLE_PAGE_JOB_TYPE = "fetch_style_page"
NORMALIZE_STYLE_PAGE_JOB_TYPE = "normalize_style_page"
STALE_RUNNING_JOB_TIMEOUT_SECONDS = 900.0
SOURCE_WORKER_LEASE_TTL_SECONDS = 120.0
SOURCE_WORKER_LEASE_HEARTBEAT_INTERVAL_SECONDS = 30.0
TAXONOMY_PAGE_KIND_TO_TYPE = {
    "taxonomy_family": "family",
    "taxonomy_type": "category",
    "taxonomy_color": "color",
    "taxonomy_decade": "decade",
    "taxonomy_origin": "region",
}
IGNORED_TAXONOMY_SECTION_TITLES = {
    "a-z",
    "see also",
    "other",
    "miscellaneous",
    "misc",
    "gallery",
    "references",
    "external links",
}
GENERIC_TAXONOMY_GROUP_TITLES = {
    "by family",
    "by family [ ]",
    "by type",
    "by type [ ]",
    "by color",
    "by color [ ]",
    "by colour",
    "by colour [ ]",
    "by decade",
    "by decade [ ]",
    "by era",
    "by era [ ]",
    "by origin",
    "by origin [ ]",
    "by country",
    "by country [ ]",
    "by region",
    "by region [ ]",
    "aesthetics by family",
    "aesthetics by type",
    "aesthetics by color",
    "aesthetics by colour",
    "aesthetics by decade",
    "aesthetics by era",
    "aesthetics by origin",
    "aesthetics by country",
    "aesthetics by region",
}


def _serialize_candidate(candidate: DiscoveredStyleCandidate) -> dict[str, str]:
    return {
        "source_name": candidate.source_name,
        "source_site": candidate.source_site,
        "source_title": candidate.source_title,
        "source_url": candidate.source_url,
    }


def _content_fingerprint(*, raw_wikitext: str | None, raw_html: str) -> str:
    source = raw_wikitext or raw_html
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _serialize_sections(sections: tuple[object, ...]) -> list[dict[str, object]]:
    return [
        {
            "section_order": getattr(section, "section_order"),
            "section_title": getattr(section, "section_title"),
            "section_level": getattr(section, "section_level"),
            "section_text": getattr(section, "section_text"),
            "section_hash": getattr(section, "section_hash"),
        }
        for section in sections
    ]


def _serialize_links(links: tuple[object, ...]) -> list[dict[str, object]]:
    return [
        {
            "anchor_text": getattr(link, "anchor_text"),
            "target_title": getattr(link, "target_title"),
            "target_url": getattr(link, "target_url"),
            "link_type": getattr(link, "link_type"),
            "section_title": getattr(link, "section_title", None),
        }
        for link in links
    ]


def _decode_wiki_title(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path or ""
    marker = "/wiki/"
    if marker not in path:
        return None
    raw_title = path.split(marker, 1)[1].strip("/")
    if not raw_title:
        return None
    return raw_title.replace("_", " ")


def _clean_taxonomy_group_label(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    if cleaned.startswith("Category:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    cleaned = cleaned.removesuffix("[ ]").strip()
    lowered = cleaned.casefold()
    if lowered in IGNORED_TAXONOMY_SECTION_TITLES:
        return None
    if lowered in GENERIC_TAXONOMY_GROUP_TITLES:
        return None
    if lowered.startswith("list of "):
        return None
    if len(cleaned) == 1 and cleaned.isalpha():
        return None
    return cleaned


class _TaxonomyContextHTMLParser(HTMLParser):
    def __init__(self, *, base_url: str, allowed_domains: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.allowed_domains = tuple(item.casefold() for item in allowed_domains)
        self.items: list[tuple[str, str]] = []
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._current_heading: str | None = None
        self._active_group_label: str | None = None
        self._link_href: str | None = None
        self._link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            try:
                self._heading_level = int(tag[1])
            except ValueError:
                self._heading_level = None
            self._heading_parts = []
            return

        if tag == "a":
            attr_map = {key: value for key, value in attrs}
            self._link_href = attr_map.get("href")
            self._link_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading_level is not None:
            heading = _clean_taxonomy_group_label("".join(self._heading_parts))
            self._current_heading = heading
            if heading:
                self._active_group_label = heading
            self._heading_level = None
            self._heading_parts = []
            return

        if tag == "a" and self._link_href:
            target_url = urljoin(self.base_url, self._link_href)
            parsed = urlparse(target_url)
            if parsed.netloc.casefold().endswith(self.allowed_domains):
                target_title = _decode_wiki_title(target_url) or " ".join(self._link_parts).strip()
                category_group = _clean_taxonomy_group_label(target_title)
                if target_title.startswith("Category:") and category_group:
                    self._active_group_label = category_group
                else:
                    label = self._active_group_label or self._current_heading
                    if label:
                        self.items.append((target_url, label))
            self._link_href = None
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        if self._heading_level is not None:
            self._heading_parts.append(data)
        if self._link_href:
            self._link_parts.append(data)


class StyleIngestJobPipeline:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.registry = AestheticsWikiSourceRegistry()
        self.scraper = HTTPStyleScraper(timeout_seconds=timeout_seconds, session_factory=SessionLocal)
        self.normalizer = DefaultStyleNormalizer()
        self.enricher = DefaultStyleEnricher()
        self.validator = DefaultStyleValidator()
        self.job_service = StyleIngestJobService()
        self.source_fetch_state_service = SourceFetchStateService()

    async def enqueue_discovery_job(
        self,
        *,
        source_name: str,
        title_contains: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> QueuedJobBatchReport:
        requested_at = datetime.now(UTC)
        title_filter = title_contains.strip() if isinstance(title_contains, str) and title_contains.strip() else None
        dedupe_key = self._discovery_job_dedupe_key(
            source_name=source_name,
            title_contains=title_filter,
            offset=offset,
            limit=limit,
            requested_at=requested_at,
        )
        async with SessionLocal() as session:
            job = await self.job_service.enqueue_job(
                session,
                source_name=source_name,
                job_type=DISCOVER_SOURCE_PAGES_JOB_TYPE,
                dedupe_key=dedupe_key,
                payload_json={
                    "source_name": source_name,
                    "title_contains": title_filter,
                    "offset": max(int(offset), 0),
                    "limit": max(int(limit), 1),
                    "requested_at": requested_at.isoformat(),
                },
                priority=50,
            )
            await session.commit()

        return QueuedJobBatchReport(
            source_name=source_name,
            discovered_count=None,
            selected_count=None,
            enqueued_count=1,
            reused_count=0,
            queued_job_id=job.id,
            queued_job_type=DISCOVER_SOURCE_PAGES_JOB_TYPE,
        )

    async def enqueue_detail_jobs_from_discovery(
        self,
        *,
        source_name: str,
        title_contains: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> QueuedJobBatchReport:
        runner = StyleBatchIngestionRunner(
            registry=self.registry,
            scraper=self.scraper,
            normalizer=self.normalizer,
            enricher=self.enricher,
            validator=self.validator,
            session_factory=SessionLocal,
        )
        selection = await runner.discover_candidates(
            source_name=source_name,
            title_contains=title_contains,
            offset=offset,
            limit=limit,
        )

        enqueued_count = 0
        reused_count = 0
        remote_states = await self.scraper.fetch_candidate_remote_states(selection.source, selection.candidates)
        remote_state_by_url = {item.source_url: item for item in remote_states}
        async with SessionLocal() as session:
            await self._persist_discovery_pages(
                session,
                source=selection.source,
                discovery_payload=selection.discovery_payload,
            )
            for candidate in selection.candidates:
                remote_state = remote_state_by_url.get(
                    candidate.source_url,
                    CandidateRemoteState(
                        source_name=selection.source.source_name,
                        source_title=candidate.source_title,
                        source_url=candidate.source_url,
                    ),
                )
                page = await self.job_service.upsert_source_page(
                    session,
                    source_name=selection.source.source_name,
                    page_url=candidate.source_url,
                    source_title=candidate.source_title,
                    page_kind="style",
                    remote_page_id=remote_state.remote_page_id,
                )
                if (
                    remote_state.remote_revision_id is not None
                    and page.latest_revision_id == remote_state.remote_revision_id
                    and page.latest_content_fingerprint
                ):
                    version = await self._load_page_version_for_revision(
                        session,
                        source_page_id=page.id,
                        remote_revision_id=remote_state.remote_revision_id,
                    )
                    if version is not None:
                        normalize_dedupe_key = self._normalize_job_dedupe_key(
                            source_name=selection.source.source_name,
                            source_page_id=page.id,
                            source_page_version_id=version.id,
                        )
                        existing_normalize_job = await self._find_job_by_dedupe_key(session, normalize_dedupe_key)
                        if existing_normalize_job is None:
                            await self.job_service.enqueue_job(
                                session,
                                source_name=selection.source.source_name,
                                job_type=NORMALIZE_STYLE_PAGE_JOB_TYPE,
                                dedupe_key=normalize_dedupe_key,
                                payload_json={
                                    "source_name": selection.source.source_name,
                                    "source_page_id": page.id,
                                    "source_page_version_id": version.id,
                                },
                                source_page_id=page.id,
                                source_page_version_id=version.id,
                                priority=100,
                            )
                            enqueued_count += 1
                            continue
                    reused_count += 1
                    continue

                dedupe_key = self._fetch_job_dedupe_key(
                    source_name=selection.source.source_name,
                    candidate_url=candidate.source_url,
                    remote_revision_id=remote_state.remote_revision_id,
                )
                existing_job = await self._find_job_by_dedupe_key(session, dedupe_key)
                await self.job_service.enqueue_job(
                    session,
                    source_name=selection.source.source_name,
                    job_type=FETCH_STYLE_PAGE_JOB_TYPE,
                    dedupe_key=dedupe_key,
                    payload_json={
                        **_serialize_candidate(candidate),
                        "remote_page_id": remote_state.remote_page_id,
                        "remote_revision_id": remote_state.remote_revision_id,
                    },
                    source_page_id=page.id,
                    priority=200,
                )
                if existing_job is None:
                    enqueued_count += 1
                else:
                    reused_count += 1
            await session.commit()

        return QueuedJobBatchReport(
            source_name=selection.source.source_name,
            discovered_count=selection.discovered_count,
            selected_count=selection.selected_count,
            enqueued_count=enqueued_count,
            reused_count=reused_count,
        )

    async def run_worker(
        self,
        *,
        source_name: str,
        idle_sleep_seconds: float = 5.0,
        max_jobs: int | None = None,
        stop_when_idle: bool = False,
    ) -> IngestWorkerRunReport:
        source = self.registry.get_source(source_name)
        lease_owner = self._build_worker_lease_owner(source_name=source_name)
        processed_jobs = 0
        succeeded_jobs = 0
        requeued_jobs = 0
        cooldown_deferred_jobs = 0
        soft_failed_jobs = 0
        hard_failed_jobs = 0
        idle_polls = 0
        last_result: ProcessedIngestJobResult | None = None

        acquired = await self._try_acquire_worker_lease(source=source, lease_owner=lease_owner)
        if not acquired:
            return self._build_worker_report(
                source_name=source_name,
                processed_jobs=processed_jobs,
                succeeded_jobs=succeeded_jobs,
                requeued_jobs=requeued_jobs,
                cooldown_deferred_jobs=cooldown_deferred_jobs,
                soft_failed_jobs=soft_failed_jobs,
                hard_failed_jobs=hard_failed_jobs,
                idle_polls=idle_polls,
                stopped_reason="source_locked",
                last_result=last_result,
            )

        heartbeat_stop = asyncio.Event()
        lease_lost = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._run_worker_lease_heartbeat(
                source=source,
                lease_owner=lease_owner,
                stop_event=heartbeat_stop,
                lease_lost_event=lease_lost,
            )
        )

        try:
            while True:
                if lease_lost.is_set():
                    return self._build_worker_report(
                        source_name=source_name,
                        processed_jobs=processed_jobs,
                        succeeded_jobs=succeeded_jobs,
                        requeued_jobs=requeued_jobs,
                        cooldown_deferred_jobs=cooldown_deferred_jobs,
                        soft_failed_jobs=soft_failed_jobs,
                        hard_failed_jobs=hard_failed_jobs,
                        idle_polls=idle_polls,
                        stopped_reason="lease_lost",
                        last_result=last_result,
                    )

                result = await self.process_next_job(source_name=source_name)
                if result is None:
                    idle_polls += 1
                    if stop_when_idle:
                        return self._build_worker_report(
                            source_name=source_name,
                            processed_jobs=processed_jobs,
                            succeeded_jobs=succeeded_jobs,
                            requeued_jobs=requeued_jobs,
                            cooldown_deferred_jobs=cooldown_deferred_jobs,
                            soft_failed_jobs=soft_failed_jobs,
                            hard_failed_jobs=hard_failed_jobs,
                            idle_polls=idle_polls,
                            stopped_reason="idle",
                            last_result=last_result,
                        )
                    try:
                        await asyncio.wait_for(lease_lost.wait(), timeout=max(idle_sleep_seconds, 0.1))
                    except asyncio.TimeoutError:
                        continue
                    return self._build_worker_report(
                        source_name=source_name,
                        processed_jobs=processed_jobs,
                        succeeded_jobs=succeeded_jobs,
                        requeued_jobs=requeued_jobs,
                        cooldown_deferred_jobs=cooldown_deferred_jobs,
                        soft_failed_jobs=soft_failed_jobs,
                        hard_failed_jobs=hard_failed_jobs,
                        idle_polls=idle_polls,
                        stopped_reason="lease_lost",
                        last_result=last_result,
                    )

                idle_polls = 0
                last_result = result
                processed_jobs += 1
                if result.status == "succeeded":
                    succeeded_jobs += 1
                elif result.status == "requeued":
                    requeued_jobs += 1
                elif result.status == COOLDOWN_DEFERRED_STATUS:
                    cooldown_deferred_jobs += 1
                elif result.status == SOFT_FAILED_STATUS:
                    soft_failed_jobs += 1
                elif result.status == HARD_FAILED_STATUS:
                    hard_failed_jobs += 1

                if max_jobs is not None and processed_jobs >= max_jobs:
                    return self._build_worker_report(
                        source_name=source_name,
                        processed_jobs=processed_jobs,
                        succeeded_jobs=succeeded_jobs,
                        requeued_jobs=requeued_jobs,
                        cooldown_deferred_jobs=cooldown_deferred_jobs,
                        soft_failed_jobs=soft_failed_jobs,
                        hard_failed_jobs=hard_failed_jobs,
                        idle_polls=idle_polls,
                        stopped_reason="max_jobs_reached",
                        last_result=last_result,
                    )
        finally:
            heartbeat_stop.set()
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._release_worker_lease(source=source, lease_owner=lease_owner)

    async def process_next_job_with_lease(self, *, source_name: str) -> tuple[str, ProcessedIngestJobResult | None]:
        source = self.registry.get_source(source_name)
        lease_owner = self._build_worker_lease_owner(source_name=source_name)
        acquired = await self._try_acquire_worker_lease(source=source, lease_owner=lease_owner)
        if not acquired:
            return "source_locked", None

        heartbeat_stop = asyncio.Event()
        lease_lost = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._run_worker_lease_heartbeat(
                source=source,
                lease_owner=lease_owner,
                stop_event=heartbeat_stop,
                lease_lost_event=lease_lost,
            )
        )
        try:
            result = await self.process_next_job(source_name=source_name)
            if lease_lost.is_set():
                return "lease_lost", result
            if result is None:
                return "idle", None
            return "processed", result
        finally:
            heartbeat_stop.set()
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._release_worker_lease(source=source, lease_owner=lease_owner)

    async def process_next_job(self, *, source_name: str) -> ProcessedIngestJobResult | None:
        async with SessionLocal() as session:
            await self.job_service.reclaim_stale_running_jobs(
                session,
                source_name=source_name,
                stale_after_seconds=STALE_RUNNING_JOB_TIMEOUT_SECONDS,
            )
            claimed = await self.job_service.claim_next_job(session, source_name=source_name)
            if claimed is None:
                await session.commit()
                return None
            job, _attempt = claimed
            await session.commit()

        if job.job_type == DISCOVER_SOURCE_PAGES_JOB_TYPE:
            return await self._process_discovery_job(job_id=job.id)
        if job.job_type == FETCH_STYLE_PAGE_JOB_TYPE:
            return await self._process_detail_job(job_id=job.id)
        if job.job_type == NORMALIZE_STYLE_PAGE_JOB_TYPE:
            return await self._process_normalize_job(job_id=job.id)

        async with SessionLocal() as session:
            job, attempt = await self._load_job_context(session, job.id)
            await self.job_service.mark_job_terminal(
                session,
                job=job,
                attempt=attempt,
                status=HARD_FAILED_STATUS,
                error_class="unsupported_job_type",
                error_message=f"Unsupported job_type={job.job_type!r}",
            )
            await session.commit()
        return ProcessedIngestJobResult(
            job_id=job.id,
            job_type=job.job_type,
            status=HARD_FAILED_STATUS,
            source_name=job.source_name,
            error_class="unsupported_job_type",
            error_message=f"Unsupported job_type={job.job_type!r}",
        )

    def _build_worker_report(
        self,
        *,
        source_name: str,
        processed_jobs: int,
        succeeded_jobs: int,
        requeued_jobs: int,
        cooldown_deferred_jobs: int,
        soft_failed_jobs: int,
        hard_failed_jobs: int,
        idle_polls: int,
        stopped_reason: str,
        last_result: ProcessedIngestJobResult | None,
    ) -> IngestWorkerRunReport:
        return IngestWorkerRunReport(
            source_name=source_name,
            processed_jobs=processed_jobs,
            succeeded_jobs=succeeded_jobs,
            requeued_jobs=requeued_jobs,
            cooldown_deferred_jobs=cooldown_deferred_jobs,
            soft_failed_jobs=soft_failed_jobs,
            hard_failed_jobs=hard_failed_jobs,
            idle_polls=idle_polls,
            stopped_reason=stopped_reason,
            last_job_id=last_result.job_id if last_result else None,
            last_job_type=last_result.job_type if last_result else None,
            last_status=last_result.status if last_result else None,
        )

    def _build_worker_lease_owner(self, *, source_name: str) -> str:
        host = socket.gethostname()
        pid = os.getpid()
        token = uuid4().hex[:12]
        return f"{source_name}:{host}:{pid}:{token}"

    async def _try_acquire_worker_lease(
        self,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
    ) -> bool:
        async with SessionLocal() as session:
            acquired, _state = await self.source_fetch_state_service.try_acquire_worker_lease(
                session,
                source=source,
                lease_owner=lease_owner,
                lease_ttl_seconds=SOURCE_WORKER_LEASE_TTL_SECONDS,
            )
            await session.commit()
        return acquired

    async def _release_worker_lease(
        self,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
    ) -> None:
        async with SessionLocal() as session:
            await self.source_fetch_state_service.release_worker_lease(
                session,
                source=source,
                lease_owner=lease_owner,
            )
            await session.commit()

    async def _run_worker_lease_heartbeat(
        self,
        *,
        source: StyleSourceRegistryEntry,
        lease_owner: str,
        stop_event: asyncio.Event,
        lease_lost_event: asyncio.Event,
    ) -> None:
        heartbeat_interval = min(
            SOURCE_WORKER_LEASE_HEARTBEAT_INTERVAL_SECONDS,
            max(SOURCE_WORKER_LEASE_TTL_SECONDS / 3.0, 1.0),
        )
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=heartbeat_interval)
                return
            except asyncio.TimeoutError:
                pass

            try:
                async with SessionLocal() as session:
                    refreshed = await self.source_fetch_state_service.refresh_worker_lease(
                        session,
                        source=source,
                        lease_owner=lease_owner,
                        lease_ttl_seconds=SOURCE_WORKER_LEASE_TTL_SECONDS,
                    )
                    await session.commit()
            except Exception:
                lease_lost_event.set()
                return

            if not refreshed:
                lease_lost_event.set()
                return

    async def _process_discovery_job(self, *, job_id: int) -> ProcessedIngestJobResult:
        async with SessionLocal() as session:
            job, _attempt = await self._load_job_context(session, job_id)
            payload = dict(job.payload_json or {})
            source = self.registry.get_source(job.source_name)
            await session.commit()

        title_contains = payload.get("title_contains")
        if not isinstance(title_contains, str) or not title_contains.strip():
            title_contains = None
        offset = max(self._coerce_int(payload.get("offset")) or 0, 0)
        limit = max(self._coerce_int(payload.get("limit")) or 20, 1)

        try:
            report = await self.enqueue_detail_jobs_from_discovery(
                source_name=source.source_name,
                title_contains=title_contains,
                offset=offset,
                limit=limit,
            )
        except Exception as exc:
            return await self._handle_failed_job(
                job_id=job_id,
                source_name=source.source_name,
                source_title=None,
                source_url=source.index_url,
                error=exc,
                job_type=DISCOVER_SOURCE_PAGES_JOB_TYPE,
            )

        async with SessionLocal() as session:
            job, attempt = await self._load_job_context(session, job_id)
            await self.job_service.mark_job_succeeded(session, job=job, attempt=attempt)
            await session.commit()

        return ProcessedIngestJobResult(
            job_id=job_id,
            job_type=DISCOVER_SOURCE_PAGES_JOB_TYPE,
            status="succeeded",
            source_name=source.source_name,
            source_url=source.index_url,
            discovered_count=report.discovered_count,
            selected_count=report.selected_count,
            enqueued_count=report.enqueued_count,
            reused_count=report.reused_count,
        )

    async def _process_detail_job(self, *, job_id: int) -> ProcessedIngestJobResult:
        async with SessionLocal() as session:
            job, _attempt = await self._load_job_context(session, job_id)
            payload = dict(job.payload_json or {})
            source = self.registry.get_source(job.source_name)
            await session.commit()

        try:
            candidate = self._deserialize_candidate(payload)
        except Exception as exc:
            return await self._handle_failed_job(
                job_id=job_id,
                source_name=source.source_name,
                source_title=None,
                source_url=None,
                error=exc,
                job_type=FETCH_STYLE_PAGE_JOB_TYPE,
            )

        try:
            scraped = await self.scraper.fetch_style_page(source, candidate)
        except Exception as exc:
            return await self._handle_failed_job(
                job_id=job_id,
                source_name=source.source_name,
                source_title=candidate.source_title,
                source_url=candidate.source_url,
                error=exc,
                job_type=FETCH_STYLE_PAGE_JOB_TYPE,
            )

        try:
            raw_snapshot = self.normalizer.normalize_page(source, scraped)
            fingerprint = raw_snapshot.content_fingerprint or _content_fingerprint(
                raw_wikitext=scraped.raw_wikitext,
                raw_html=scraped.raw_html,
            )
            async with SessionLocal() as session:
                job, attempt = await self._load_job_context(session, job_id)
                page = await self._load_or_create_source_page(
                    session,
                    source=source,
                    candidate=candidate,
                    job=job,
                )
                if scraped.page_id is not None:
                    page.remote_page_id = scraped.page_id

                version = await self.job_service.register_page_version(
                    session,
                    source_page=page,
                    fetch_mode=scraped.fetch_mode,
                    remote_revision_id=scraped.revision_id,
                    content_fingerprint=fingerprint,
                    raw_html=scraped.raw_html,
                    raw_wikitext=scraped.raw_wikitext,
                    raw_text=raw_snapshot.raw_text,
                    raw_sections_json=_serialize_sections(raw_snapshot.sections),
                    raw_links_json=_serialize_links(raw_snapshot.links),
                    fetched_at=scraped.fetched_at,
                )

                normalize_dedupe_key = self._normalize_job_dedupe_key(
                    source_name=source.source_name,
                    source_page_id=page.id,
                    source_page_version_id=version.id,
                )
                normalize_job = await self.job_service.enqueue_job(
                    session,
                    source_name=source.source_name,
                    job_type=NORMALIZE_STYLE_PAGE_JOB_TYPE,
                    dedupe_key=normalize_dedupe_key,
                    payload_json={
                        "source_name": source.source_name,
                        "source_page_id": page.id,
                        "source_page_version_id": version.id,
                    },
                    source_page_id=page.id,
                    source_page_version_id=version.id,
                    priority=100,
                )

                job.source_page_id = page.id
                job.source_page_version_id = version.id
                await self.job_service.mark_job_succeeded(session, job=job, attempt=attempt)
                await session.commit()

                return ProcessedIngestJobResult(
                    job_id=job.id,
                    job_type=job.job_type,
                    status="succeeded",
                    source_name=job.source_name,
                    source_title=page.source_title,
                    source_url=page.page_url,
                    source_page_id=page.id,
                    source_page_version_id=version.id,
                    normalize_job_id=normalize_job.id,
                )
        except Exception as exc:
            return await self._handle_failed_job(
                job_id=job_id,
                source_name=source.source_name,
                source_title=candidate.source_title,
                source_url=candidate.source_url,
                error=exc,
                job_type=FETCH_STYLE_PAGE_JOB_TYPE,
            )

    async def _process_normalize_job(self, *, job_id: int) -> ProcessedIngestJobResult:
        async with SessionLocal() as session:
            job, attempt = await self._load_job_context(session, job_id)
            source = self.registry.get_source(job.source_name)

            try:
                payload = dict(job.payload_json or {})
                source_page = await self._load_source_page(session, payload["source_page_id"])
                version = await self._load_source_page_version(session, payload["source_page_version_id"])
                scraped = self._build_scraped_page(
                    source=source,
                    source_page=source_page,
                    version=version,
                )
                normalized = self.normalizer.normalize_page(source, scraped)
                enriched = self.enricher.enrich(normalized)
                validated = self.validator.validate(enriched)
                if not validated.is_valid:
                    raise ValueError("; ".join(validated.errors) or "validated style document is invalid")

                writer = SQLAlchemyStyleDBWriter(session)
                payload_obj = build_style_persistence_payload(validated)
                taxonomy_records_from_discovery = await self._build_taxonomy_records_from_discovery_pages(
                    session,
                    source_name=source.source_name,
                    candidate_url=source_page.page_url,
                )
                if taxonomy_records_from_discovery:
                    payload_obj = self._with_extra_taxonomy_records(
                        payload=payload_obj,
                        extra_records=taxonomy_records_from_discovery,
                    )
                result = await writer.persist(payload_obj)
                version.raw_text = normalized.raw_text
                version.raw_sections_json = _serialize_sections(normalized.sections)
                version.raw_links_json = _serialize_links(normalized.links)
                job.source_page_id = source_page.id
                job.source_page_version_id = version.id
                await self.job_service.mark_job_succeeded(session, job=job, attempt=attempt)
                await session.commit()

                return ProcessedIngestJobResult(
                    job_id=job.id,
                    job_type=job.job_type,
                    status="succeeded",
                    source_name=job.source_name,
                    source_title=source_page.source_title,
                    source_url=source_page.page_url,
                    source_page_id=source_page.id,
                    source_page_version_id=version.id,
                    style_id=result.style_id,
                    style_slug=result.style_slug,
                )
            except Exception as exc:
                await session.rollback()
                return await self._handle_failed_job(
                    job_id=job_id,
                    source_name=source.source_name,
                    source_title=source_page.source_title if "source_page" in locals() else None,
                    source_url=source_page.page_url if "source_page" in locals() else None,
                    error=exc,
                    job_type=NORMALIZE_STYLE_PAGE_JOB_TYPE,
                    source_page_id=source_page.id if "source_page" in locals() else None,
                    source_page_version_id=version.id if "version" in locals() else None,
                )

    async def _handle_failed_job(
        self,
        *,
        job_id: int,
        source_name: str,
        source_title: str | None,
        source_url: str | None,
        error: Exception,
        job_type: str,
        source_page_id: int | None = None,
        source_page_version_id: int | None = None,
    ) -> ProcessedIngestJobResult:
        async with SessionLocal() as session:
            source = self.registry.get_source(source_name)
            job, attempt = await self._load_job_context(session, job_id)
            state = await self.source_fetch_state_service.get_or_create(session, source=source)

            error_class = error.__class__.__name__
            error_message = str(error)

            if state.mode == "cooldown" and state.next_allowed_at is not None:
                await self.job_service.mark_job_terminal(
                    session,
                    job=job,
                    attempt=attempt,
                    status=COOLDOWN_DEFERRED_STATUS,
                    http_status=state.last_http_status,
                    error_class=error_class,
                    error_message=error_message,
                    cooldown_until=state.next_allowed_at,
                )
                await session.commit()
                return ProcessedIngestJobResult(
                    job_id=job.id,
                    job_type=job_type,
                    status=COOLDOWN_DEFERRED_STATUS,
                    source_name=source_name,
                    source_title=source_title,
                    source_url=source_url,
                    source_page_id=source_page_id,
                    source_page_version_id=source_page_version_id,
                    error_class=error_class,
                    error_message=error_message,
                    cooldown_until=state.next_allowed_at,
                )

            if state.mode == "blocked_suspected":
                error_message = f"{error_message}; source {source_name!r} is in blocked_suspected mode"
                terminal_status = HARD_FAILED_STATUS
            else:
                terminal_status = SOFT_FAILED_STATUS if self._is_retryable_error(job_type=job_type, error=error) else HARD_FAILED_STATUS

            if terminal_status == SOFT_FAILED_STATUS and job.attempt_count < max(int(source.crawl_policy.max_retries), 1):
                retry_at = self._calculate_retry_at(
                    source=source,
                    state_interval_seconds=state.current_min_interval_sec,
                    attempt_count=job.attempt_count,
                )
                await self.job_service.mark_job_requeued(
                    session,
                    job=job,
                    attempt=attempt,
                    available_at=retry_at,
                    http_status=state.last_http_status,
                    error_class=error_class,
                    error_message=error_message,
                )
                await session.commit()
                return ProcessedIngestJobResult(
                    job_id=job.id,
                    job_type=job_type,
                    status="requeued",
                    source_name=source_name,
                    source_title=source_title,
                    source_url=source_url,
                    source_page_id=source_page_id,
                    source_page_version_id=source_page_version_id,
                    error_class=error_class,
                    error_message=error_message,
                    cooldown_until=retry_at,
                )

            await self.job_service.mark_job_terminal(
                session,
                job=job,
                attempt=attempt,
                status=terminal_status,
                http_status=state.last_http_status,
                error_class=error_class,
                error_message=error_message,
            )
            await session.commit()
            return ProcessedIngestJobResult(
                job_id=job.id,
                job_type=job_type,
                status=terminal_status,
                source_name=source_name,
                source_title=source_title,
                source_url=source_url,
                source_page_id=source_page_id,
                source_page_version_id=source_page_version_id,
                error_class=error_class,
                error_message=error_message,
            )

    def _is_retryable_error(self, *, job_type: str, error: Exception) -> bool:
        if job_type == DISCOVER_SOURCE_PAGES_JOB_TYPE:
            return isinstance(error, (RuntimeError, ValueError))
        if job_type == FETCH_STYLE_PAGE_JOB_TYPE:
            return isinstance(error, (RuntimeError, ValueError))
        if job_type == NORMALIZE_STYLE_PAGE_JOB_TYPE:
            return isinstance(error, RuntimeError)
        return False

    def _calculate_retry_at(
        self,
        *,
        source: StyleSourceRegistryEntry,
        state_interval_seconds: float | None,
        attempt_count: int,
    ) -> datetime:
        base_interval = max(
            float(source.crawl_policy.retry_backoff_seconds),
            float(state_interval_seconds or 0.0),
            float(source.crawl_policy.min_delay_seconds),
        )
        multiplier = max(2 ** max(attempt_count - 1, 0), 1)
        return datetime.now(UTC) + timedelta(seconds=base_interval * multiplier)

    async def _find_job_by_dedupe_key(self, session: AsyncSession, dedupe_key: str) -> StyleIngestJob | None:
        result = await session.execute(
            select(StyleIngestJob).where(StyleIngestJob.dedupe_key == dedupe_key).limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_job_context(
        self,
        session: AsyncSession,
        job_id: int,
    ) -> tuple[StyleIngestJob, StyleIngestAttempt]:
        job = await session.get(StyleIngestJob, job_id)
        if job is None:
            raise ValueError(f"style_ingest_job {job_id} was not found")

        attempt = (
            await session.execute(
                select(StyleIngestAttempt)
                .where(StyleIngestAttempt.job_id == job_id)
                .order_by(StyleIngestAttempt.attempt_number.desc(), StyleIngestAttempt.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if attempt is None:
            raise ValueError(f"style_ingest_attempt for job {job_id} was not found")

        return job, attempt

    async def _load_source_page(self, session: AsyncSession, source_page_id: int) -> StyleSourcePage:
        source_page = await session.get(StyleSourcePage, source_page_id)
        if source_page is None:
            raise ValueError(f"style_source_page {source_page_id} was not found")
        return source_page

    async def _load_source_page_version(
        self,
        session: AsyncSession,
        source_page_version_id: int,
    ) -> StyleSourcePageVersion:
        version = await session.get(StyleSourcePageVersion, source_page_version_id)
        if version is None:
            raise ValueError(f"style_source_page_version {source_page_version_id} was not found")
        return version

    async def _load_page_version_for_revision(
        self,
        session: AsyncSession,
        *,
        source_page_id: int,
        remote_revision_id: int,
    ) -> StyleSourcePageVersion | None:
        result = await session.execute(
            select(StyleSourcePageVersion)
            .where(
                StyleSourcePageVersion.source_page_id == source_page_id,
                StyleSourcePageVersion.remote_revision_id == remote_revision_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _persist_discovery_pages(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        discovery_payload: object | None,
    ) -> None:
        if not isinstance(discovery_payload, dict):
            return
        pages = discovery_payload.get("pages")
        if not isinstance(pages, list):
            return

        for item in pages:
            if not isinstance(item, dict):
                continue

            page_title = item.get("title")
            page_url = item.get("page_url")
            raw_html = item.get("text")
            if not isinstance(page_title, str) or not page_title.strip():
                continue
            if not isinstance(page_url, str) or not page_url.strip():
                continue
            if not isinstance(raw_html, str):
                raw_html = ""

            discovery_page = ScrapedStylePage(
                source_name=source.source_name,
                source_site=source.source_site,
                source_title=page_title,
                source_url=page_url,
                fetched_at=datetime.now(UTC),
                raw_html=raw_html,
                fetch_mode=source.discovery_fetch_mode,
                page_id=self._coerce_int(item.get("pageid")),
                revision_id=self._coerce_int(item.get("revid")),
                raw_wikitext=None,
            )
            raw_snapshot = self.normalizer.normalize_page(source, discovery_page)
            page = await self.job_service.upsert_source_page(
                session,
                source_name=source.source_name,
                page_url=page_url,
                source_title=page_title,
                page_kind=str(item.get("page_kind") or "discovery_page"),
                remote_page_id=discovery_page.page_id,
                discovered_at=discovery_page.fetched_at,
            )
            await self.job_service.register_page_version(
                session,
                source_page=page,
                fetch_mode=discovery_page.fetch_mode,
                remote_revision_id=discovery_page.revision_id,
                content_fingerprint=raw_snapshot.content_fingerprint,
                raw_html=discovery_page.raw_html,
                raw_wikitext=None,
                raw_text=raw_snapshot.raw_text,
                raw_sections_json=_serialize_sections(raw_snapshot.sections),
                raw_links_json=_serialize_links(raw_snapshot.links),
                fetched_at=discovery_page.fetched_at,
            )

    async def _load_or_create_source_page(
        self,
        session: AsyncSession,
        *,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
        job: StyleIngestJob,
    ) -> StyleSourcePage:
        page = await session.get(StyleSourcePage, job.source_page_id) if job.source_page_id is not None else None
        if page is not None:
            page.source_title = candidate.source_title
            page.page_url = candidate.source_url
            page.page_kind = "style"
            return page

        return await self.job_service.upsert_source_page(
            session,
            source_name=source.source_name,
            page_url=candidate.source_url,
            source_title=candidate.source_title,
            page_kind="style",
        )

    def _deserialize_candidate(self, payload: dict[str, object]) -> DiscoveredStyleCandidate:
        return DiscoveredStyleCandidate(
            source_name=str(payload["source_name"]),
            source_site=str(payload["source_site"]),
            source_title=str(payload["source_title"]),
            source_url=str(payload["source_url"]),
        )

    def _build_scraped_page(
        self,
        *,
        source: StyleSourceRegistryEntry,
        source_page: StyleSourcePage,
        version: StyleSourcePageVersion,
    ) -> ScrapedStylePage:
        return ScrapedStylePage(
            source_name=source.source_name,
            source_site=source.source_site,
            source_title=source_page.source_title,
            source_url=source_page.page_url,
            fetched_at=version.fetched_at,
            raw_html=version.raw_html,
            fetch_mode=version.fetch_mode,
            page_id=source_page.remote_page_id,
            revision_id=version.remote_revision_id,
            raw_wikitext=version.raw_wikitext,
        )

    def _normalize_job_dedupe_key(
        self,
        *,
        source_name: str,
        source_page_id: int,
        source_page_version_id: int,
    ) -> str:
        return f"{source_name}:{NORMALIZE_STYLE_PAGE_JOB_TYPE}:{source_page_id}:{source_page_version_id}"

    def _fetch_job_dedupe_key(
        self,
        *,
        source_name: str,
        candidate_url: str,
        remote_revision_id: int | None,
    ) -> str:
        revision_part = str(remote_revision_id) if remote_revision_id is not None else "unknown"
        return f"{source_name}:{FETCH_STYLE_PAGE_JOB_TYPE}:{candidate_url}:{revision_part}"

    def _discovery_job_dedupe_key(
        self,
        *,
        source_name: str,
        title_contains: str | None,
        offset: int,
        limit: int,
        requested_at: datetime,
    ) -> str:
        title_part = title_contains or "*"
        return (
            f"{source_name}:{DISCOVER_SOURCE_PAGES_JOB_TYPE}:{offset}:{limit}:{title_part}:"
            f"{requested_at.isoformat()}"
        )

    async def _build_taxonomy_records_from_discovery_pages(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        candidate_url: str,
    ) -> tuple[dict[str, object], ...]:
        result = await session.execute(
            select(StyleSourcePage)
            .where(
                StyleSourcePage.source_name == source_name,
                StyleSourcePage.page_kind.in_(tuple(TAXONOMY_PAGE_KIND_TO_TYPE)),
            )
            .order_by(StyleSourcePage.id.asc())
        )
        pages = result.scalars().all()
        if not pages:
            return ()

        records: dict[tuple[str, str], dict[str, object]] = {}
        source = self.registry.get_source(source_name)
        for page in pages:
            version = await self._load_latest_page_version(session, page)
            if version is None:
                continue

            taxonomy_type = TAXONOMY_PAGE_KIND_TO_TYPE.get(page.page_kind)
            if taxonomy_type is None:
                continue

            html_context_labels = self._extract_taxonomy_context_labels(
                raw_html=version.raw_html,
                base_url=page.page_url,
                allowed_domains=source.allowed_domains,
                candidate_url=candidate_url,
            )

            labels = list(html_context_labels)
            if not labels:
                for link in version.raw_links_json or []:
                    if not isinstance(link, dict):
                        continue
                    target_url = link.get("target_url")
                    if not isinstance(target_url, str) or target_url != candidate_url:
                        continue
                    section_title = self._normalize_taxonomy_section_title(link.get("section_title"))
                    if section_title is None:
                        continue
                    labels.append(section_title)

            for label in labels:
                slug = slugify(label)
                if not slug:
                    continue
                key = (taxonomy_type, slug)
                current = records.get(key)
                candidate = {
                    "taxonomy_type": taxonomy_type,
                    "name": label,
                    "slug": slug,
                    "description": None,
                    "link_strength": 0.98,
                    "evidence_kind": "taxonomy_page_section",
                    "evidence_text": f"{page.source_title}: {label}",
                }
                if current is None or float(candidate["link_strength"]) > float(current["link_strength"]):
                    records[key] = candidate

        return tuple(records.values())

    async def _load_latest_page_version(
        self,
        session: AsyncSession,
        source_page: StyleSourcePage,
    ) -> StyleSourcePageVersion | None:
        query = select(StyleSourcePageVersion).where(StyleSourcePageVersion.source_page_id == source_page.id)
        if source_page.latest_revision_id is not None:
            query = query.where(StyleSourcePageVersion.remote_revision_id == source_page.latest_revision_id)
        elif source_page.latest_content_fingerprint:
            query = query.where(StyleSourcePageVersion.content_fingerprint == source_page.latest_content_fingerprint)

        result = await session.execute(
            query.order_by(StyleSourcePageVersion.fetched_at.desc(), StyleSourcePageVersion.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    def _normalize_taxonomy_section_title(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        return _clean_taxonomy_group_label(value)

    def _extract_taxonomy_context_labels(
        self,
        *,
        raw_html: str,
        base_url: str,
        allowed_domains: tuple[str, ...],
        candidate_url: str,
    ) -> tuple[str, ...]:
        if not raw_html:
            return ()
        parser = _TaxonomyContextHTMLParser(base_url=base_url, allowed_domains=allowed_domains)
        parser.feed(raw_html)
        labels: list[str] = []
        for target_url, label in parser.items:
            if target_url != candidate_url:
                continue
            normalized = _clean_taxonomy_group_label(label)
            if normalized and normalized not in labels:
                labels.append(normalized)
        return tuple(labels)

    def _with_extra_taxonomy_records(
        self,
        *,
        payload,
        extra_records: tuple[dict[str, object], ...],
    ):
        merged: dict[tuple[str, str], dict[str, object]] = {
            (str(record["taxonomy_type"]), str(record["slug"])): dict(record)
            for record in payload.taxonomy_records
        }
        for record in extra_records:
            key = (str(record["taxonomy_type"]), str(record["slug"]))
            current = merged.get(key)
            if current is None or float(record.get("link_strength", 0.0)) > float(current.get("link_strength", 0.0)):
                merged[key] = dict(record)

        return type(payload)(
            source_record=payload.source_record,
            section_records=payload.section_records,
            link_records=payload.link_records,
            style_record=payload.style_record,
            alias_records=payload.alias_records,
            profile_record=payload.profile_record,
            trait_records=payload.trait_records,
            taxonomy_records=tuple(merged.values()),
            relation_records=payload.relation_records,
        )

    def _coerce_int(self, value: object) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
