import unittest

from app.ingestion.styles.contracts import ProcessedIngestJobResult, SourceCrawlPolicy, StyleSourceRegistryEntry
from app.ingestion.styles.job_pipeline import StyleIngestJobPipeline


class _FakeRegistry:
    def __init__(self, source: StyleSourceRegistryEntry) -> None:
        self._source = source

    def get_source(self, source_name: str) -> StyleSourceRegistryEntry:
        if source_name != self._source.source_name:
            raise ValueError(source_name)
        return self._source


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


class _BaseLoggingPipeline(StyleIngestJobPipeline):
    def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
        super().__init__(timeout_seconds=0.1, progress_reporter=lambda event, payload: events.append((event, payload)))
        self.registry = _FakeRegistry(_build_source())

    async def _try_acquire_worker_lease(self, *, source, lease_owner):  # type: ignore[override]
        return True

    async def _release_worker_lease(self, *, source, lease_owner):  # type: ignore[override]
        return None

    async def _run_worker_lease_heartbeat(self, *, source, lease_owner, stop_event, lease_lost_event):  # type: ignore[override]
        await stop_event.wait()

    async def _build_queue_snapshot(self, *, source_name: str) -> dict[str, object]:  # type: ignore[override]
        return {
            "queued_jobs": 0,
            "cooldown_jobs": 0,
            "running_jobs": 0,
            "claimable_jobs": 0,
            "future_jobs": 0,
            "next_available_at": None,
        }


class _SuccessfulLoggingPipeline(_BaseLoggingPipeline):
    def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
        super().__init__(events)
        self._remaining_results = [
            ProcessedIngestJobResult(
                job_id=101,
                job_type="fetch_style_page",
                status="succeeded",
                source_name="aesthetics_wiki",
                source_title="Dark Academia",
                source_url="https://aesthetics.fandom.com/wiki/Dark_Academia",
                was_style_created=True,
                persist_outcome="created",
            ),
            None,
        ]

    async def process_next_job(self, *, source_name: str):  # type: ignore[override]
        next_result = self._remaining_results.pop(0)
        if next_result is None:
            return None
        self._emit_progress(
            "job_claimed",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
        )
        self._emit_progress(
            "job_started",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
            source_title=next_result.source_title,
            source_url=next_result.source_url,
        )
        self._emit_progress(
            "detail_job_started",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
            source_title=next_result.source_title,
            source_url=next_result.source_url,
        )
        return next_result


class _FailingLoggingPipeline(_BaseLoggingPipeline):
    def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
        super().__init__(events)
        self._remaining_results = [
            ProcessedIngestJobResult(
                job_id=202,
                job_type="fetch_style_page",
                status="hard_failed",
                source_name="aesthetics_wiki",
                source_title="Dark Academia",
                source_url="https://aesthetics.fandom.com/wiki/Dark_Academia",
                error_class="DonorApiError",
                error_message="access denied",
            ),
            None,
        ]

    async def process_next_job(self, *, source_name: str):  # type: ignore[override]
        next_result = self._remaining_results.pop(0)
        if next_result is None:
            return None
        self._emit_progress(
            "job_claimed",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
        )
        self._emit_progress(
            "job_started",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
            source_title=next_result.source_title,
            source_url=next_result.source_url,
        )
        self._emit_progress(
            "job_failed",
            source_name=source_name,
            job_id=next_result.job_id,
            job_type=next_result.job_type,
            source_title=next_result.source_title,
            source_url=next_result.source_url,
            status=next_result.status,
            error_class=next_result.error_class,
            error_message=next_result.error_message,
        )
        return next_result


class StyleIngestionPipelineLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_emits_claim_start_success_and_wait_events(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        pipeline = _SuccessfulLoggingPipeline(events)

        report = await pipeline.run_worker(
            source_name="aesthetics_wiki",
            idle_sleep_seconds=5.0,
            max_jobs=5,
            stop_when_idle=True,
        )

        self.assertEqual(report.processed_jobs, 1)
        self.assertEqual(report.created_styles_count, 1)
        event_names = [event_name for event_name, _payload in events]
        self.assertIn("worker_lease_acquired", event_names)
        self.assertIn("job_claimed", event_names)
        self.assertIn("job_started", event_names)
        self.assertIn("detail_job_started", event_names)
        self.assertIn("job_finished", event_names)
        self.assertIn("worker_idle", event_names)
        self.assertIn("worker_lease_released", event_names)

    async def test_worker_emits_failed_job_event_before_waiting(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        pipeline = _FailingLoggingPipeline(events)

        report = await pipeline.run_worker(
            source_name="aesthetics_wiki",
            idle_sleep_seconds=5.0,
            max_jobs=5,
            stop_when_idle=True,
        )

        self.assertEqual(report.hard_failed_jobs, 1)
        event_names = [event_name for event_name, _payload in events]
        self.assertIn("job_claimed", event_names)
        self.assertIn("job_started", event_names)
        self.assertIn("job_failed", event_names)
        self.assertIn("worker_idle", event_names)
