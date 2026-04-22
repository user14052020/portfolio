import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.ingestion.styles.style_chatgpt_batch_runner import DefaultStyleChatGptEnrichmentBatchRunner
from app.ingestion.styles.structured_logging import StructuredIngestionLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ChatGPT-based style enrichment from DB source text.")
    parser.add_argument(
        "--mode",
        choices=("single", "batch", "full-backfill", "retry-failed"),
        default="single",
    )
    parser.add_argument("--style-id", type=int, help="Single style id for --mode single.")
    parser.add_argument(
        "--style-ids",
        help="Optional comma-separated style ids for explicit batch selection in --mode batch.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional batch limit.")
    parser.add_argument("--offset", type=int, default=0, help="Optional batch offset.")
    parser.add_argument("--dry-run", action="store_true", help="Run enrichment without writing facet rows or logs.")
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Process styles even if the current facet version already exists.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.mode == "single" and args.style_id is None:
        raise ValueError("single mode requires --style-id")
    if args.mode != "single" and args.style_id is not None:
        raise ValueError("--style-id is only supported in single mode")
    if args.offset < 0:
        raise ValueError("--offset must be greater than or equal to 0")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than 0")
    if args.mode == "single" and args.style_ids:
        raise ValueError("--style-ids is not supported in single mode")
    if args.mode in {"full-backfill", "retry-failed"} and args.style_ids:
        raise ValueError(f"--style-ids is not supported in {args.mode} mode")


def parse_style_ids(raw_value: str | None) -> list[int] | None:
    if not raw_value:
        return None
    parsed: list[int] = []
    for part in raw_value.split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        parsed.append(int(cleaned))
    return parsed or None


async def main_async(args: argparse.Namespace) -> dict[str, object]:
    event_logger = StructuredIngestionLogger(logger_name="app.ingestion.styles.enrichment", mirror_stream=sys.stdout)
    event_logger.emit(
        "style_enrichment_command_started",
        {
            "mode": args.mode,
            "style_id": args.style_id,
            "style_ids": args.style_ids,
            "limit": args.limit,
            "offset": args.offset,
            "dry_run": args.dry_run,
            "overwrite_existing": args.overwrite_existing,
        },
    )
    runner = DefaultStyleChatGptEnrichmentBatchRunner(
        session_factory=SessionLocal,
        progress_reporter=event_logger.as_reporter(),
    )

    try:
        if args.mode == "single":
            result = await runner.run(
                style_ids=[args.style_id],
                limit=None,
                offset=0,
                dry_run=args.dry_run,
                overwrite_existing=args.overwrite_existing,
            )
        elif args.mode == "batch":
            result = await runner.run(
                style_ids=parse_style_ids(args.style_ids),
                limit=args.limit,
                offset=args.offset,
                dry_run=args.dry_run,
                overwrite_existing=args.overwrite_existing,
            )
        elif args.mode == "full-backfill":
            result = await runner.run(
                style_ids=None,
                limit=args.limit,
                offset=args.offset,
                dry_run=args.dry_run,
                overwrite_existing=args.overwrite_existing,
            )
        else:
            result = await runner.run_retry_failed(
                limit=args.limit,
                offset=args.offset,
                dry_run=args.dry_run,
                overwrite_existing=args.overwrite_existing,
            )
    except Exception as exc:  # noqa: BLE001
        event_logger.emit(
            "style_enrichment_command_failed",
            {
                "mode": args.mode,
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        raise

    payload = {
        "mode": args.mode,
        "selected_count": result.selected_count,
        "processed_count": result.processed_count,
        "succeeded_count": result.succeeded_count,
        "failed_count": result.failed_count,
        "skipped_existing_count": result.skipped_existing_count,
        "dry_run": result.dry_run,
        "overwrite_existing": result.overwrite_existing,
        "items": [
            {
                "style_id": item.style_id,
                "style_slug": item.style_slug,
                "status": item.status,
                "did_write": item.did_write,
                "source_page_id": item.source_page_id,
                "error_message": item.error_message,
            }
            for item in result.items
        ],
    }
    event_logger.emit(
        "style_enrichment_command_finished",
        {
            "mode": args.mode,
            "selected_count": result.selected_count,
            "processed_count": result.processed_count,
            "succeeded_count": result.succeeded_count,
            "failed_count": result.failed_count,
            "skipped_existing_count": result.skipped_existing_count,
            "dry_run": result.dry_run,
            "overwrite_existing": result.overwrite_existing,
        },
    )
    return payload


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)
    payload = asyncio.run(main_async(args))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
