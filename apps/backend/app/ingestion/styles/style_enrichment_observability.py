from __future__ import annotations

from typing import Any

from app.ingestion.styles.style_chatgpt_prompt_builder import (
    STYLE_ENRICHMENT_PROMPT_VERSION,
    STYLE_ENRICHMENT_SCHEMA_VERSION,
)


SUCCESSFUL_ENRICHMENT_STATUSES = frozenset({"succeeded", "dry_run_succeeded", "skipped_existing"})


def infer_enrichment_validation_status(status: str) -> str:
    if status in {"succeeded", "dry_run_succeeded", "failed_write"}:
        return "passed"
    if status == "failed_validation":
        return "failed"
    if status == "skipped_existing":
        return "skipped"
    if status == "started":
        return "pending"
    return "not_reached"


def infer_enrichment_write_status(*, status: str, did_write: bool) -> str:
    if status == "succeeded" and did_write:
        return "written"
    if status == "dry_run_succeeded":
        return "dry_run"
    if status == "failed_write":
        return "failed"
    if status == "skipped_existing":
        return "skipped_existing"
    if status == "started":
        return "pending"
    return "not_written"


def build_style_enrichment_run_event_payload(
    *,
    style_id: int,
    source_page_id: int | None,
    provider: str,
    model_name: str,
    status: str,
    attempts: int,
    did_write: bool,
    dry_run: bool,
    error_class: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    validation_status = infer_enrichment_validation_status(status)
    write_status = infer_enrichment_write_status(status=status, did_write=did_write)
    success = status in SUCCESSFUL_ENRICHMENT_STATUSES

    return {
        "style_id": style_id,
        "source_page_id": source_page_id,
        "provider": provider,
        "model": model_name,
        "prompt_version": STYLE_ENRICHMENT_PROMPT_VERSION,
        "schema_version": STYLE_ENRICHMENT_SCHEMA_VERSION,
        "status": status,
        "success": success,
        "validation_status": validation_status,
        "write_status": write_status,
        "attempts": max(attempts, 0),
        "dry_run": dry_run,
        "error_class": error_class,
        "error_message": error_message,
    }


def build_style_enrichment_run_metric_payload(run_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_name": "style_enrichment_runs_total",
        "value": 1,
        "tags": {
            "provider": run_payload["provider"],
            "model": run_payload["model"],
            "status": run_payload["status"],
            "success": run_payload["success"],
            "validation_status": run_payload["validation_status"],
            "write_status": run_payload["write_status"],
            "dry_run": run_payload["dry_run"],
        },
    }


def build_style_enrichment_batch_metrics_payload(
    *,
    selected_count: int,
    processed_count: int,
    succeeded_count: int,
    failed_count: int,
    skipped_existing_count: int,
    dry_run: bool,
    overwrite_existing: bool,
) -> dict[str, Any]:
    success_rate = None
    if processed_count > 0:
        success_rate = round(succeeded_count / processed_count, 4)

    return {
        "selected_count": selected_count,
        "processed_count": processed_count,
        "succeeded_count": succeeded_count,
        "failed_count": failed_count,
        "skipped_existing_count": skipped_existing_count,
        "success_rate": success_rate,
        "dry_run": dry_run,
        "overwrite_existing": overwrite_existing,
    }
