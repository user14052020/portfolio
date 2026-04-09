import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.ingestion.styles.batch_runner import DEFAULT_BATCH_LIMIT, StyleBatchIngestionRunner
from app.ingestion.styles.contracts import CandidateBatchSelection, DiscoveredStyleCandidate, StyleSourceRegistryEntry
from app.ingestion.styles.job_pipeline import StyleIngestJobPipeline
from app.ingestion.styles.runner import StyleIngestionRunner
from app.ingestion.styles.style_db_writer import SQLAlchemyStyleDBWriter
from app.ingestion.styles.style_enricher import DefaultStyleEnricher
from app.ingestion.styles.style_matcher import StyleDirectionMatcher
from app.ingestion.styles.style_merge_service import StyleDirectionMergeService
from app.ingestion.styles.style_normalizer import DefaultStyleNormalizer
from app.ingestion.styles.style_review_service import (
    CONFIRM_RESOLUTION,
    REJECT_RESOLUTION,
    StyleDirectionReviewService,
)
from app.ingestion.styles.style_scraper import HTTPStyleScraper
from app.ingestion.styles.style_source_registry import AestheticsWikiSourceRegistry
from app.ingestion.styles.style_validator import DefaultStyleValidator
from app.models.style_ingest_run import StyleIngestRun


RESUMABLE_BATCH_STATUSES = {"failed", "aborted", "completed_with_failures"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run style ingestion against a trusted source.")
    parser.add_argument(
        "--mode",
        choices=(
            "single",
            "discover",
            "batch",
            "enqueue-jobs",
            "process-next-job",
            "run-worker",
            "match",
            "review-list",
            "review-resolve",
            "merge",
            "run-list",
            "run-abort",
        ),
        default="single",
    )
    parser.add_argument("--source-name", default="aesthetics_wiki", help="Registered ingestion source name.")
    parser.add_argument("--style-title", help="Style title used for canonical record creation in single mode.")
    parser.add_argument("--style-url", help="Trusted source page URL for the style in single mode.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="HTTP timeout for source fetch.")
    parser.add_argument("--title-contains", help="Batch/discovery filter by partial style title.")
    parser.add_argument("--offset", type=int, default=0, help="Offset inside discovered candidate list.")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_BATCH_LIMIT,
        help="Maximum number of discovered candidates to process in batch/discovery mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="In single mode fetch/normalize/validate without DB write. In batch mode only list selected candidates.",
    )
    parser.add_argument("--review-limit", type=int, default=50, help="Maximum number of pending review items to show.")
    parser.add_argument("--match-id", type=int, help="Persistent style_direction_matches.id for manual review action.")
    parser.add_argument(
        "--resolution",
        choices=(CONFIRM_RESOLUTION, REJECT_RESOLUTION),
        help="Manual review resolution for review-resolve mode.",
    )
    parser.add_argument(
        "--style-direction-id",
        type=int,
        help="Selected style_directions.id for confirm_candidate resolution.",
    )
    parser.add_argument("--review-note", help="Optional operator note saved into manual review resolution.")
    parser.add_argument("--merge-limit", type=int, default=100, help="Maximum number of eligible matches to merge.")
    parser.add_argument("--resume-run-id", type=int, help="Existing style_ingest_runs.id for batch resume.")
    parser.add_argument("--run-limit", type=int, default=20, help="Maximum number of ingest runs to show in run-list mode.")
    parser.add_argument("--run-id", type=int, help="Target style_ingest_runs.id for operator actions.")
    parser.add_argument("--worker-max-jobs", type=int, help="Maximum number of queued jobs to process in run-worker mode.")
    parser.add_argument(
        "--worker-idle-seconds",
        type=float,
        default=5.0,
        help="Sleep interval between idle polls in run-worker mode.",
    )
    parser.add_argument(
        "--worker-stop-when-idle",
        action="store_true",
        help="Stop run-worker when no queued jobs are currently available.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.mode == "single":
        if not args.style_title or not args.style_url:
            raise ValueError("single mode requires both --style-title and --style-url")

    if args.mode in {"discover", "batch", "enqueue-jobs", "match"}:
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0")
        if args.offset < 0:
            raise ValueError("--offset must be greater than or equal to 0")

    if args.mode == "process-next-job" and args.dry_run:
        raise ValueError("process-next-job does not support --dry-run")

    if args.mode == "run-worker":
        if args.dry_run:
            raise ValueError("run-worker does not support --dry-run")
        if args.worker_max_jobs is not None and args.worker_max_jobs <= 0:
            raise ValueError("--worker-max-jobs must be greater than 0")
        if args.worker_idle_seconds <= 0:
            raise ValueError("--worker-idle-seconds must be greater than 0")

    if args.mode == "review-list" and args.review_limit <= 0:
        raise ValueError("--review-limit must be greater than 0")

    if args.mode == "review-resolve":
        if args.dry_run:
            raise ValueError("review-resolve does not support --dry-run because it persists a manual decision")
        if args.match_id is None:
            raise ValueError("review-resolve mode requires --match-id")
        if not args.resolution:
            raise ValueError("review-resolve mode requires --resolution")
        if args.resolution == CONFIRM_RESOLUTION and args.style_direction_id is None:
            raise ValueError("confirm_candidate resolution requires --style-direction-id")

    if args.mode == "merge" and args.merge_limit <= 0:
        raise ValueError("--merge-limit must be greater than 0")

    if args.mode == "run-list" and args.run_limit <= 0:
        raise ValueError("--run-limit must be greater than 0")

    if args.mode == "run-abort" and args.run_id is None:
        raise ValueError("run-abort mode requires --run-id")

    if args.resume_run_id is not None:
        if args.mode != "batch":
            raise ValueError("--resume-run-id is supported only for --mode batch")
        if args.dry_run:
            raise ValueError("batch resume does not support --dry-run")


def resolve_source(source_name: str) -> StyleSourceRegistryEntry:
    registry = AestheticsWikiSourceRegistry()
    return registry.get_source(source_name)


def build_candidate(args: argparse.Namespace, source: StyleSourceRegistryEntry) -> DiscoveredStyleCandidate:
    return DiscoveredStyleCandidate(
        source_name=source.source_name,
        source_site=source.source_site,
        source_title=args.style_title,
        source_url=args.style_url,
    )


async def create_ingest_run(
    *,
    source: StyleSourceRegistryEntry,
    source_url: str,
    run_mode: str,
) -> int:
    async with SessionLocal() as session:
        run = StyleIngestRun(
            started_at=datetime.now(UTC),
            source_name=source.source_name,
            source_url=source_url,
            run_status="running",
            checkpoint_json={"mode": run_mode},
            parser_version=source.parser_version,
            normalizer_version=source.normalizer_version,
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        await session.commit()
        return run_id


async def ensure_no_other_active_batch_runs(
    *,
    source_name: str,
    current_run_id: int | None = None,
) -> None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(StyleIngestRun).where(
                StyleIngestRun.source_name == source_name,
                StyleIngestRun.run_status == "running",
            )
        )
        active_runs = []
        for run in result.scalars().all():
            if current_run_id is not None and run.id == current_run_id:
                continue
            checkpoint = run.checkpoint_json or {}
            if checkpoint.get("mode") == "batch":
                active_runs.append(run.id)

    if active_runs:
        joined = ", ".join(str(item) for item in active_runs)
        raise ValueError(
            f"Another batch ingestion run is already active for source {source_name!r}: {joined}. "
            "Resume the existing run or wait for it to finish."
        )


async def finalize_ingest_run(
    run_id: int,
    *,
    source: StyleSourceRegistryEntry,
    source_url: str,
    run_status: str,
    styles_seen: int,
    styles_matched: int,
    styles_created: int,
    styles_updated: int,
    styles_failed: int,
) -> None:
    async with SessionLocal() as session:
        run = await session.get(StyleIngestRun, run_id)
        if run is None:
            return
        run.finished_at = datetime.now(UTC)
        run.run_status = run_status
        run.source_url = source_url
        run.styles_seen = styles_seen
        run.styles_matched = styles_matched
        run.styles_created = styles_created
        run.styles_updated = styles_updated
        run.styles_failed = styles_failed
        run.parser_version = source.parser_version
        run.normalizer_version = source.normalizer_version
        await session.commit()


def build_single_runner(*, timeout_seconds: float, writer: SQLAlchemyStyleDBWriter | None = None) -> StyleIngestionRunner:
    return StyleIngestionRunner(
        scraper=HTTPStyleScraper(timeout_seconds=timeout_seconds, session_factory=SessionLocal),
        normalizer=DefaultStyleNormalizer(),
        enricher=DefaultStyleEnricher(),
        validator=DefaultStyleValidator(),
        writer=writer,
    )


def build_batch_runner(*, timeout_seconds: float) -> StyleBatchIngestionRunner:
    scraper = HTTPStyleScraper(timeout_seconds=timeout_seconds, session_factory=SessionLocal)
    return StyleBatchIngestionRunner(
        registry=AestheticsWikiSourceRegistry(),
        scraper=scraper,
        normalizer=DefaultStyleNormalizer(),
        enricher=DefaultStyleEnricher(),
        validator=DefaultStyleValidator(),
        session_factory=SessionLocal,
    )


def _serialize_candidate(candidate: DiscoveredStyleCandidate) -> dict[str, str]:
    return {
        "source_name": candidate.source_name,
        "source_site": candidate.source_site,
        "source_title": candidate.source_title,
        "source_url": candidate.source_url,
    }


def is_resumable_batch_run(*, mode: str | None, run_status: str, next_index: int, selected_count: int) -> bool:
    if mode != "batch":
        return False
    if run_status not in RESUMABLE_BATCH_STATUSES:
        return False
    return next_index < selected_count


def is_abortable_batch_run(*, mode: str | None, run_status: str) -> bool:
    return mode == "batch" and run_status == "running"


def calculate_active_error_type(
    *,
    mode: str | None,
    last_error: str | None,
    fatal_error: str | None,
) -> str | None:
    if mode != "batch":
        return None
    if fatal_error:
        return "fatal"
    if last_error:
        return "candidate"
    return None


def is_batch_completed_normally(
    *,
    mode: str | None,
    run_status: str,
    styles_failed: int,
    next_index: int,
    selected_count: int,
) -> bool | None:
    if mode != "batch":
        return None
    return run_status == "completed" and styles_failed == 0 and next_index >= selected_count


def calculate_terminal_state_family(
    *,
    mode: str | None,
    run_status: str,
    completed_normally: bool | None,
) -> str | None:
    if mode != "batch":
        return None
    if run_status == "running":
        return "active"
    if completed_normally:
        return "successful_terminal"
    if run_status in {"failed", "aborted", "completed_with_failures"}:
        return "attention_terminal"
    return "other_terminal"


def calculate_batch_progress_percent(*, mode: str | None, next_index: int, selected_count: int) -> float | None:
    if mode != "batch":
        return None
    if selected_count <= 0:
        return 100.0
    safe_next_index = min(max(next_index, 0), selected_count)
    return round((safe_next_index / selected_count) * 100, 2)


def calculate_batch_remaining_count(*, mode: str | None, next_index: int, selected_count: int) -> int | None:
    if mode != "batch":
        return None
    if selected_count <= 0:
        return 0
    safe_next_index = min(max(next_index, 0), selected_count)
    return selected_count - safe_next_index


async def initialize_batch_checkpoint(run_id: int, selection: CandidateBatchSelection) -> None:
    checkpoint = {
        "mode": "batch",
        "source_name": selection.source.source_name,
        "source_site": selection.source.source_site,
        "source_url": selection.source.index_url,
        "discovered_count": selection.discovered_count,
        "selected_count": selection.selected_count,
        "next_index": 0,
        "processed_count": 0,
        "created_count": 0,
        "updated_count": 0,
        "failed_count": 0,
        "last_attempted_source_title": None,
        "last_attempted_source_url": None,
        "last_error": None,
        "candidates": [_serialize_candidate(candidate) for candidate in selection.candidates],
    }
    async with SessionLocal() as session:
        run = await session.get(StyleIngestRun, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found for checkpoint initialization")
        run.checkpoint_json = checkpoint
        run.run_status = "running"
        await session.commit()


async def update_run_checkpoint_fields(run_id: int, **fields: object) -> None:
    async with SessionLocal() as session:
        run = await session.get(StyleIngestRun, run_id)
        if run is None:
            return
        checkpoint = dict(run.checkpoint_json or {})
        checkpoint.update(fields)
        run.checkpoint_json = checkpoint
        await session.commit()


async def load_batch_checkpoint(run_id: int) -> tuple[StyleIngestRun, CandidateBatchSelection, int, dict[str, int]]:
    async with SessionLocal() as session:
        run = await session.get(StyleIngestRun, run_id)
        if run is None:
            raise ValueError(f"style_ingest_run {run_id} was not found")

        checkpoint = run.checkpoint_json or {}
        if checkpoint.get("mode") != "batch":
            raise ValueError(f"style_ingest_run {run_id} does not contain a batch checkpoint")

        source_name = checkpoint.get("source_name") or run.source_name
        source = resolve_source(source_name)
        serialized_candidates = checkpoint.get("candidates") or []
        candidates = tuple(
            DiscoveredStyleCandidate(
                source_name=item["source_name"],
                source_site=item["source_site"],
                source_title=item["source_title"],
                source_url=item["source_url"],
            )
            for item in serialized_candidates
        )
        selection = CandidateBatchSelection(
            source=source,
            discovered_count=int(checkpoint.get("discovered_count", len(candidates))),
            selected_count=int(checkpoint.get("selected_count", len(candidates))),
            candidates=candidates,
        )
        counters = {
            "processed_count": int(checkpoint.get("processed_count", 0)),
            "created_count": int(checkpoint.get("created_count", 0)),
            "updated_count": int(checkpoint.get("updated_count", 0)),
            "failed_count": int(checkpoint.get("failed_count", 0)),
        }
        next_index = int(checkpoint.get("next_index", 0))
        if not is_resumable_batch_run(
            mode=checkpoint.get("mode"),
            run_status=run.run_status,
            next_index=next_index,
            selected_count=selection.selected_count,
        ):
            raise ValueError(
                f"style_ingest_run {run_id} is not resumable: "
                f"status={run.run_status!r}, next_index={next_index}, selected_count={selection.selected_count}"
            )
        run.run_status = "running"
        checkpoint["fatal_error"] = None
        run.checkpoint_json = checkpoint
        await session.commit()
        return run, selection, next_index, counters


async def run_single_mode(args: argparse.Namespace) -> int:
    source = resolve_source(args.source_name)
    candidate = build_candidate(args, source)

    if args.dry_run:
        runner = build_single_runner(timeout_seconds=args.timeout_seconds)
        document = await runner.process_candidate(source=source, candidate=candidate)
        print(
            json.dumps(
                {
                    "mode": "single-dry-run",
                    "is_valid": document.is_valid,
                    "warnings": list(document.warnings),
                    "errors": list(document.errors),
                    "canonical_name": document.enriched.canonical_name,
                    "slug": document.enriched.slug,
                    "source_url": candidate.source_url,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if document.is_valid else 1

    run_id = await create_ingest_run(source=source, source_url=candidate.source_url, run_mode="single")
    try:
        async with SessionLocal() as session:
            writer = SQLAlchemyStyleDBWriter(session, run_id=run_id)
            runner = build_single_runner(timeout_seconds=args.timeout_seconds, writer=writer)
            document, result = await runner.process_and_persist(source=source, candidate=candidate)
            await session.commit()

        await finalize_ingest_run(
            run_id,
            source=source,
            source_url=candidate.source_url,
            run_status="completed",
            styles_seen=1,
            styles_matched=1,
            styles_created=1 if result.was_style_created else 0,
            styles_updated=1 if result.was_style_updated else 0,
            styles_failed=0,
        )
        print(
            json.dumps(
                {
                    "mode": "single-persist",
                    "run_id": run_id,
                    "style_id": result.style_id,
                    "style_slug": result.style_slug,
                    "source_id": result.source_id,
                    "warnings": list(document.warnings),
                    "was_source_created": result.was_source_created,
                    "was_style_created": result.was_style_created,
                    "was_style_updated": result.was_style_updated,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception:
        await finalize_ingest_run(
            run_id,
            source=source,
            source_url=candidate.source_url,
            run_status="failed",
            styles_seen=1,
            styles_matched=0,
            styles_created=0,
            styles_updated=0,
            styles_failed=1,
        )
        raise


async def build_selection(args: argparse.Namespace) -> CandidateBatchSelection:
    batch_runner = build_batch_runner(timeout_seconds=args.timeout_seconds)
    return await batch_runner.discover_candidates(
        source_name=args.source_name,
        title_contains=args.title_contains,
        offset=args.offset,
        limit=args.limit,
    )


async def run_discover_mode(args: argparse.Namespace) -> int:
    selection = await build_selection(args)
    print(
        json.dumps(
            {
                "mode": "discover",
                "source_name": selection.source.source_name,
                "discovered_count": selection.discovered_count,
                "selected_count": selection.selected_count,
                "limit": args.limit,
                "offset": args.offset,
                "title_contains": args.title_contains,
                "candidates": [
                    {
                        "source_title": item.source_title,
                        "source_url": item.source_url,
                    }
                    for item in selection.candidates
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_enqueue_jobs_mode(args: argparse.Namespace) -> int:
    pipeline = StyleIngestJobPipeline(timeout_seconds=args.timeout_seconds)
    report = await pipeline.enqueue_discovery_job(
        source_name=args.source_name,
        title_contains=args.title_contains,
        offset=args.offset,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "mode": "enqueue-jobs",
                "source_name": report.source_name,
                "discovered_count": report.discovered_count,
                "selected_count": report.selected_count,
                "enqueued_count": report.enqueued_count,
                "reused_count": report.reused_count,
                "queued_job_id": report.queued_job_id,
                "queued_job_type": report.queued_job_type,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_process_next_job_mode(args: argparse.Namespace) -> int:
    pipeline = StyleIngestJobPipeline(timeout_seconds=args.timeout_seconds)
    stopped_reason, result = await pipeline.process_next_job_with_lease(source_name=args.source_name)
    if result is None:
        print(
            json.dumps(
                {
                    "mode": "process-next-job",
                    "source_name": args.source_name,
                    "claimed": False,
                    "stopped_reason": stopped_reason,
                    "job": None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "mode": "process-next-job",
                "source_name": result.source_name,
                "claimed": result.job_id > 0,
                "stopped_reason": stopped_reason,
                "job": {
                    "job_id": result.job_id,
                    "job_type": result.job_type,
                    "status": result.status,
                    "source_title": result.source_title,
                    "source_url": result.source_url,
                    "source_page_id": result.source_page_id,
                    "source_page_version_id": result.source_page_version_id,
                    "style_id": result.style_id,
                    "style_slug": result.style_slug,
                    "detail_job_id": result.detail_job_id,
                    "normalize_job_id": result.normalize_job_id,
                    "error_class": result.error_class,
                    "error_message": result.error_message,
                    "cooldown_until": result.cooldown_until.isoformat() if result.cooldown_until else None,
                    "discovered_count": result.discovered_count,
                    "selected_count": result.selected_count,
                    "enqueued_count": result.enqueued_count,
                    "reused_count": result.reused_count,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_worker_mode(args: argparse.Namespace) -> int:
    pipeline = StyleIngestJobPipeline(timeout_seconds=args.timeout_seconds)
    report = await pipeline.run_worker(
        source_name=args.source_name,
        idle_sleep_seconds=args.worker_idle_seconds,
        max_jobs=args.worker_max_jobs,
        stop_when_idle=args.worker_stop_when_idle,
    )
    print(
        json.dumps(
            {
                "mode": "run-worker",
                "source_name": report.source_name,
                "processed_jobs": report.processed_jobs,
                "succeeded_jobs": report.succeeded_jobs,
                "requeued_jobs": report.requeued_jobs,
                "cooldown_deferred_jobs": report.cooldown_deferred_jobs,
                "soft_failed_jobs": report.soft_failed_jobs,
                "hard_failed_jobs": report.hard_failed_jobs,
                "idle_polls": report.idle_polls,
                "stopped_reason": report.stopped_reason,
                "last_job_id": report.last_job_id,
                "last_job_type": report.last_job_type,
                "last_status": report.last_status,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_batch_mode(args: argparse.Namespace) -> int:
    if args.dry_run:
        selection = await build_selection(args)
        print(
            json.dumps(
                {
                    "mode": "batch-dry-run",
                    "source_name": selection.source.source_name,
                    "discovered_count": selection.discovered_count,
                    "selected_count": selection.selected_count,
                    "limit": args.limit,
                    "offset": args.offset,
                    "title_contains": args.title_contains,
                    "candidates": [
                        {
                            "source_title": item.source_title,
                            "source_url": item.source_url,
                        }
                        for item in selection.candidates
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    resumed_from_index = 0
    if args.resume_run_id is not None:
        run, selection, resumed_from_index, counters = await load_batch_checkpoint(args.resume_run_id)
        run_id = run.id
        source = selection.source
        await ensure_no_other_active_batch_runs(source_name=source.source_name, current_run_id=run_id)
    else:
        selection = await build_selection(args)
        await ensure_no_other_active_batch_runs(source_name=selection.source.source_name)
        run_id = await create_ingest_run(
            source=selection.source,
            source_url=selection.source.index_url,
            run_mode="batch",
        )
        await initialize_batch_checkpoint(run_id, selection)
        counters = {
            "processed_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "failed_count": 0,
        }
        source = selection.source

    try:
        batch_runner = build_batch_runner(timeout_seconds=args.timeout_seconds)
        report = await batch_runner.run_batch(
            selection=selection,
            run_id=run_id,
            start_index=resumed_from_index,
            processed_count=counters["processed_count"],
            created_count=counters["created_count"],
            updated_count=counters["updated_count"],
            failed_count=counters["failed_count"],
        )
        await update_run_checkpoint_fields(run_id, fatal_error=None)
        final_run_status = "completed_with_failures" if report.failed_count > 0 else "completed"
        await finalize_ingest_run(
            run_id,
            source=source,
            source_url=source.index_url,
            run_status=final_run_status,
            styles_seen=report.selected_count,
            styles_matched=report.processed_count,
            styles_created=report.created_count,
            styles_updated=report.updated_count,
            styles_failed=report.failed_count,
        )
        print(
            json.dumps(
                {
                    "mode": "batch-persist",
                    "run_id": run_id,
                    "source_name": report.source_name,
                    "discovered_count": report.discovered_count,
                    "selected_count": report.selected_count,
                    "processed_count": report.processed_count,
                    "created_count": report.created_count,
                    "updated_count": report.updated_count,
                    "failed_count": report.failed_count,
                    "resumed_from_index": resumed_from_index,
                    "failures": [
                        {
                            "source_title": item.source_title,
                            "source_url": item.source_url,
                            "error": item.error,
                        }
                        for item in report.failures
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if report.failed_count == 0 else 1
    except Exception as exc:
        checkpoint_counters = counters
        try:
            _, _, _, checkpoint_counters = await load_batch_checkpoint(run_id)
        except Exception:
            checkpoint_counters = counters
        await update_run_checkpoint_fields(run_id, fatal_error=str(exc))
        await finalize_ingest_run(
            run_id,
            source=source,
            source_url=source.index_url,
            run_status="failed",
            styles_seen=selection.selected_count,
            styles_matched=checkpoint_counters.get("processed_count", 0),
            styles_created=checkpoint_counters.get("created_count", 0),
            styles_updated=checkpoint_counters.get("updated_count", 0),
            styles_failed=max(checkpoint_counters.get("failed_count", 0), 1),
        )
        raise


async def run_match_mode(args: argparse.Namespace) -> int:
    selection = await build_selection(args)
    matcher = StyleDirectionMatcher()

    async with SessionLocal() as session:
        report = await matcher.match_selection(session, selection=selection, persist=not args.dry_run)
        if not args.dry_run:
            await session.commit()

    print(
        json.dumps(
            {
                "mode": "match",
                "source_name": report.source_name,
                "discovered_count": report.discovered_count,
                "selected_count": report.selected_count,
                "auto_matched_count": report.auto_matched_count,
                "ambiguous_count": report.ambiguous_count,
                "unmatched_count": report.unmatched_count,
                "persisted": not args.dry_run,
                "decisions": [
                    {
                        "source_title": item.source_title,
                        "source_url": item.source_url,
                        "discovered_slug": item.discovered_slug,
                        "match_status": item.match_status,
                        "matched_style_direction_id": item.matched_style_direction_id,
                        "match_method": item.match_method,
                        "match_score": item.match_score,
                        "candidate_count": item.candidate_count,
                        "candidate_options": [
                            {
                                "style_direction_id": option.style_direction_id,
                                "style_direction_slug": option.style_direction_slug,
                                "style_direction_title": option.style_direction_title,
                                "match_method": option.match_method,
                                "match_score": option.match_score,
                            }
                            for option in item.candidate_options
                        ],
                    }
                    for item in report.decisions
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_review_list_mode(args: argparse.Namespace) -> int:
    service = StyleDirectionReviewService()
    async with SessionLocal() as session:
        items = await service.list_pending_reviews(
            session,
            limit=args.review_limit,
            source_name=args.source_name,
        )

    print(
        json.dumps(
            {
                "mode": "review-list",
                "source_name": args.source_name,
                "pending_count": len(items),
                "items": [
                    {
                        "review_id": item.review_id,
                        "match_id": item.match_id,
                        "source_name": item.source_name,
                        "source_url": item.source_url,
                        "source_title": item.source_title,
                        "discovered_slug": item.discovered_slug,
                        "review_status": item.review_status,
                        "match_status": item.match_status,
                        "queued_at": item.queued_at.isoformat(),
                        "candidate_count": item.candidate_count,
                        "candidate_options": [
                            {
                                "style_direction_id": option.style_direction_id,
                                "style_direction_slug": option.style_direction_slug,
                                "style_direction_title": option.style_direction_title,
                                "match_method": option.match_method,
                                "match_score": option.match_score,
                            }
                            for option in item.candidate_options
                        ],
                    }
                    for item in items
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_review_resolve_mode(args: argparse.Namespace) -> int:
    service = StyleDirectionReviewService()
    async with SessionLocal() as session:
        result = await service.resolve_review(
            session,
            match_id=args.match_id,
            resolution=args.resolution,
            selected_style_direction_id=args.style_direction_id,
            review_note=args.review_note,
        )
        await session.commit()

    print(
        json.dumps(
            {
                "mode": "review-resolve",
                "review_id": result.review_id,
                "match_id": result.match_id,
                "source_name": result.source_name,
                "source_url": result.source_url,
                "source_title": result.source_title,
                "discovered_slug": result.discovered_slug,
                "review_status": result.review_status,
                "match_status": result.match_status,
                "selected_style_direction_id": result.selected_style_direction_id,
                "resolution_type": result.resolution_type,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_merge_mode(args: argparse.Namespace) -> int:
    service = StyleDirectionMergeService()
    async with SessionLocal() as session:
        report = await service.merge_matches(
            session,
            source_name=args.source_name,
            limit=args.merge_limit,
            persist=not args.dry_run,
        )
        if not args.dry_run:
            await session.commit()

    print(
        json.dumps(
            {
                "mode": "merge",
                "source_name": args.source_name,
                "selected_count": report.selected_count,
                "merged_count": report.merged_count,
                "skipped_count": report.skipped_count,
                "persisted": not args.dry_run,
                "items": [
                    {
                        "match_id": item.match_id,
                        "source_name": item.source_name,
                        "source_url": item.source_url,
                        "source_title": item.source_title,
                        "discovered_slug": item.discovered_slug,
                        "match_status": item.match_status,
                        "style_direction_id": item.style_direction_id,
                        "canonical_style_id": item.canonical_style_id,
                        "canonical_style_slug": item.canonical_style_slug,
                        "merge_status": item.merge_status,
                        "link_status": item.link_status,
                        "confidence_score": item.confidence_score,
                    }
                    for item in report.items
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_run_list_mode(args: argparse.Namespace) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            select(StyleIngestRun)
            .where(StyleIngestRun.source_name == args.source_name)
            .order_by(StyleIngestRun.started_at.desc(), StyleIngestRun.id.desc())
            .limit(args.run_limit)
        )
        runs = result.scalars().all()

    items = []
    for run in runs:
        checkpoint = run.checkpoint_json or {}
        mode = checkpoint.get("mode")
        next_index = int(checkpoint.get("next_index", 0))
        selected_count = int(checkpoint.get("selected_count", run.styles_seen))
        progress_percent = calculate_batch_progress_percent(
            mode=mode,
            next_index=next_index,
            selected_count=selected_count,
        )
        remaining_count = calculate_batch_remaining_count(
            mode=mode,
            next_index=next_index,
            selected_count=selected_count,
        )
        last_error = checkpoint.get("last_error")
        fatal_error = checkpoint.get("fatal_error")
        active_error_type = calculate_active_error_type(
            mode=mode,
            last_error=last_error,
            fatal_error=fatal_error,
        )
        completed_normally = is_batch_completed_normally(
            mode=mode,
            run_status=run.run_status,
            styles_failed=run.styles_failed,
            next_index=next_index,
            selected_count=selected_count,
        )
        terminal_state_family = calculate_terminal_state_family(
            mode=mode,
            run_status=run.run_status,
            completed_normally=completed_normally,
        )
        resume_available = is_resumable_batch_run(
            mode=mode,
            run_status=run.run_status,
            next_index=next_index,
            selected_count=selected_count,
        )
        abort_available = is_abortable_batch_run(mode=mode, run_status=run.run_status)
        items.append(
            {
                "run_id": run.id,
                "source_name": run.source_name,
                "source_url": run.source_url,
                "run_status": run.run_status,
                "mode": mode,
                "started_at": run.started_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "styles_seen": run.styles_seen,
                "styles_matched": run.styles_matched,
                "styles_created": run.styles_created,
                "styles_updated": run.styles_updated,
                "styles_failed": run.styles_failed,
                "parser_version": run.parser_version,
                "normalizer_version": run.normalizer_version,
                "checkpoint_next_index": next_index,
                "checkpoint_selected_count": selected_count,
                "progress_percent": progress_percent,
                "remaining_count": remaining_count,
                "last_attempted_source_title": checkpoint.get("last_attempted_source_title"),
                "last_attempted_source_url": checkpoint.get("last_attempted_source_url"),
                "last_error": last_error,
                "fatal_error": fatal_error,
                "active_error_type": active_error_type,
                "completed_normally": completed_normally,
                "terminal_state_family": terminal_state_family,
                "resume_available": resume_available,
                "abort_available": abort_available,
            }
        )

    print(
        json.dumps(
            {
                "mode": "run-list",
                "source_name": args.source_name,
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_run_abort_mode(args: argparse.Namespace) -> int:
    async with SessionLocal() as session:
        run = await session.get(StyleIngestRun, args.run_id)
        if run is None:
            raise ValueError(f"style_ingest_run {args.run_id} was not found")

        checkpoint = run.checkpoint_json or {}
        if checkpoint.get("mode") != "batch":
            raise ValueError(f"style_ingest_run {args.run_id} is not a batch run")
        if run.run_status == "completed":
            raise ValueError(f"style_ingest_run {args.run_id} is already completed")

        run.run_status = "aborted"
        if run.finished_at is None:
            run.finished_at = datetime.now(UTC)
        await session.commit()

        payload = {
            "mode": "run-abort",
            "run_id": run.id,
            "source_name": run.source_name,
            "run_status": run.run_status,
            "checkpoint_next_index": int((run.checkpoint_json or {}).get("next_index", 0)),
            "checkpoint_selected_count": int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
            "progress_percent": calculate_batch_progress_percent(
                mode=(run.checkpoint_json or {}).get("mode"),
                next_index=int((run.checkpoint_json or {}).get("next_index", 0)),
                selected_count=int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
            ),
            "remaining_count": calculate_batch_remaining_count(
                mode=(run.checkpoint_json or {}).get("mode"),
                next_index=int((run.checkpoint_json or {}).get("next_index", 0)),
                selected_count=int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
            ),
            "completed_normally": is_batch_completed_normally(
                mode=(run.checkpoint_json or {}).get("mode"),
                run_status=run.run_status,
                styles_failed=run.styles_failed,
                next_index=int((run.checkpoint_json or {}).get("next_index", 0)),
                selected_count=int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
            ),
            "terminal_state_family": calculate_terminal_state_family(
                mode=(run.checkpoint_json or {}).get("mode"),
                run_status=run.run_status,
                completed_normally=is_batch_completed_normally(
                    mode=(run.checkpoint_json or {}).get("mode"),
                    run_status=run.run_status,
                    styles_failed=run.styles_failed,
                    next_index=int((run.checkpoint_json or {}).get("next_index", 0)),
                    selected_count=int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
                ),
            ),
            "resume_available": is_resumable_batch_run(
                mode=(run.checkpoint_json or {}).get("mode"),
                run_status=run.run_status,
                next_index=int((run.checkpoint_json or {}).get("next_index", 0)),
                selected_count=int((run.checkpoint_json or {}).get("selected_count", run.styles_seen)),
            ),
            "abort_available": is_abortable_batch_run(
                mode=(run.checkpoint_json or {}).get("mode"),
                run_status=run.run_status,
            ),
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


async def run_ingestion(args: argparse.Namespace) -> int:
    if args.mode == "single":
        return await run_single_mode(args)
    if args.mode == "discover":
        return await run_discover_mode(args)
    if args.mode == "batch":
        return await run_batch_mode(args)
    if args.mode == "enqueue-jobs":
        return await run_enqueue_jobs_mode(args)
    if args.mode == "process-next-job":
        return await run_process_next_job_mode(args)
    if args.mode == "run-worker":
        return await run_worker_mode(args)
    if args.mode == "match":
        return await run_match_mode(args)
    if args.mode == "review-list":
        return await run_review_list_mode(args)
    if args.mode == "review-resolve":
        return await run_review_resolve_mode(args)
    if args.mode == "merge":
        return await run_merge_mode(args)
    if args.mode == "run-list":
        return await run_run_list_mode(args)
    if args.mode == "run-abort":
        return await run_run_abort_mode(args)
    raise ValueError(f"Unsupported mode={args.mode!r}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)
    return asyncio.run(run_ingestion(args))


if __name__ == "__main__":
    raise SystemExit(main())
