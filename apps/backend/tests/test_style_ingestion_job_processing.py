from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.ingestion.styles.contracts import (
    QueuedJobBatchReport,
    ScrapedStylePage,
    SourceCrawlPolicy,
    StyleSourceRegistryEntry,
)
from app.ingestion.styles.job_pipeline import (
    DISCOVER_SOURCE_PAGES_JOB_TYPE,
    FETCH_STYLE_PAGE_JOB_TYPE,
    NORMALIZE_STYLE_PAGE_JOB_TYPE,
    StyleIngestJobPipeline,
)


class _FakeRegistry:
    def __init__(self, source: StyleSourceRegistryEntry) -> None:
        self._source = source

    def get_source(self, source_name: str) -> StyleSourceRegistryEntry:
        if source_name != self._source.source_name:
            raise ValueError(source_name)
        return self._source


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeSessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _DiscoveryJobService:
    def __init__(self) -> None:
        self.marked_succeeded_job_ids: list[int] = []

    async def mark_job_succeeded(self, session, *, job, attempt) -> None:
        self.marked_succeeded_job_ids.append(job.id)


class _DetailJobService:
    def __init__(self) -> None:
        self.marked_succeeded_job_ids: list[int] = []

    async def register_page_version(
        self,
        session,
        *,
        source_page,
        fetch_mode,
        remote_revision_id,
        content_fingerprint,
        raw_html,
        raw_wikitext,
        raw_text,
        raw_sections_json,
        raw_links_json,
        fetched_at,
    ):
        return SimpleNamespace(id=601)

    async def enqueue_job(
        self,
        session,
        *,
        source_name,
        job_type,
        dedupe_key,
        payload_json,
        source_page_id,
        source_page_version_id,
        priority,
    ):
        return SimpleNamespace(id=701)

    async def mark_job_succeeded(self, session, *, job, attempt) -> None:
        self.marked_succeeded_job_ids.append(job.id)


def _build_source() -> StyleSourceRegistryEntry:
    return StyleSourceRegistryEntry(
        source_name="aesthetics_wiki",
        source_site="aesthetics.fandom.com",
        index_url="https://aesthetics.fandom.com/wiki/List_of_Aesthetics",
        discovery_page_titles=("List of Aesthetics",),
        allowed_domains=("aesthetics.fandom.com",),
        parser_version="0.2.0",
        normalizer_version="0.2.0",
        crawl_policy=SourceCrawlPolicy(
            user_agent="TestBot/1.0",
            min_delay_seconds=0.0,
            max_delay_seconds=0.0,
            retry_backoff_seconds=0.0,
        ),
        api_endpoint_url="https://aesthetics.fandom.com/api.php",
    )


class _DiscoveryPipeline(StyleIngestJobPipeline):
    def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
        super().__init__(timeout_seconds=0.1, progress_reporter=lambda event, payload: events.append((event, payload)))
        self.registry = _FakeRegistry(_build_source())
        self.job_service = _DiscoveryJobService()
        self._job = SimpleNamespace(
            id=11,
            source_name="aesthetics_wiki",
            payload_json={"offset": 0, "limit": 5, "title_contains": None},
        )
        self._attempt = SimpleNamespace(id=1)

    async def _load_job_context(self, session, job_id):  # type: ignore[override]
        return self._job, self._attempt

    async def enqueue_detail_jobs_from_discovery(self, *, source_name, title_contains, offset, limit):  # type: ignore[override]
        return QueuedJobBatchReport(
            source_name=source_name,
            discovered_count=1036,
            selected_count=5,
            enqueued_count=5,
            reused_count=0,
        )


class _DetailPipeline(StyleIngestJobPipeline):
    def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
        super().__init__(timeout_seconds=0.1, progress_reporter=lambda event, payload: events.append((event, payload)))
        self.registry = _FakeRegistry(_build_source())
        self.job_service = _DetailJobService()
        self.scraper = SimpleNamespace(fetch_style_page=self._fetch_style_page)
        self.normalizer = SimpleNamespace(
            normalize_page=lambda source, scraped: SimpleNamespace(
                raw_text="normalized",
                sections=(),
                links=(),
                content_fingerprint="fingerprint-1",
            )
        )
        self._job = SimpleNamespace(
            id=21,
            source_name="aesthetics_wiki",
            job_type=FETCH_STYLE_PAGE_JOB_TYPE,
            payload_json={
                "source_name": "aesthetics_wiki",
                "source_site": "aesthetics.fandom.com",
                "source_title": "Dark Academia",
                "source_url": "https://aesthetics.fandom.com/wiki/Dark_Academia",
            },
            source_page_id=None,
            source_page_version_id=None,
        )
        self._attempt = SimpleNamespace(id=2)

    async def _load_job_context(self, session, job_id):  # type: ignore[override]
        return self._job, self._attempt

    async def _load_or_create_source_page(self, session, *, source, candidate, job):  # type: ignore[override]
        return SimpleNamespace(
            id=501,
            source_title=candidate.source_title,
            page_url=candidate.source_url,
            remote_page_id=None,
        )

    async def _fetch_style_page(self, source, candidate) -> ScrapedStylePage:
        return ScrapedStylePage(
            source_name=source.source_name,
            source_site=source.source_site,
            source_title=candidate.source_title,
            source_url=candidate.source_url,
            fetched_at=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
            raw_html="<main>Dark Academia</main>",
            raw_wikitext="== Dark Academia ==",
            page_id=1106,
            revision_id=224819,
        )


class StyleIngestionJobProcessingTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_discovery_job_emits_detail_enqueue_summary(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        pipeline = _DiscoveryPipeline(events)

        with patch("app.ingestion.styles.job_pipeline.SessionLocal", new=_FakeSessionFactory()):
            result = await pipeline._process_discovery_job(job_id=11)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.enqueued_count, 5)
        self.assertEqual(pipeline.job_service.marked_succeeded_job_ids, [11])
        event_names = [name for name, _payload in events]
        self.assertIn("job_started", event_names)
        self.assertIn("discovery_job_started", event_names)
        self.assertIn("discovery_detail_jobs_enqueued", event_names)

    async def test_process_detail_job_succeeds_and_enqueues_normalize_job(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        pipeline = _DetailPipeline(events)

        with patch("app.ingestion.styles.job_pipeline.SessionLocal", new=_FakeSessionFactory()):
            result = await pipeline._process_detail_job(job_id=21)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.job_type, FETCH_STYLE_PAGE_JOB_TYPE)
        self.assertEqual(result.source_page_id, 501)
        self.assertEqual(result.source_page_version_id, 601)
        self.assertEqual(result.normalize_job_id, 701)
        self.assertEqual(pipeline.job_service.marked_succeeded_job_ids, [21])
        event_names = [name for name, _payload in events]
        self.assertIn("job_started", event_names)
        self.assertIn("detail_job_started", event_names)
