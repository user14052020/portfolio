import unittest

from app.ingestion.styles.style_enrichment_observability import (
    build_style_enrichment_batch_metrics_payload,
    build_style_enrichment_run_event_payload,
    build_style_enrichment_run_metric_payload,
)
from app.ingestion.styles.style_chatgpt_prompt_builder import (
    STYLE_ENRICHMENT_PROMPT_VERSION,
    STYLE_ENRICHMENT_SCHEMA_VERSION,
)


class StyleEnrichmentObservabilityTests(unittest.TestCase):
    def test_run_event_payload_includes_required_enrichment_log_fields(self) -> None:
        payload = build_style_enrichment_run_event_payload(
            style_id=42,
            source_page_id=101,
            provider="openai",
            model_name="gpt-test",
            status="succeeded",
            attempts=2,
            did_write=True,
            dry_run=False,
        )

        self.assertEqual(payload["style_id"], 42)
        self.assertEqual(payload["source_page_id"], 101)
        self.assertEqual(payload["provider"], "openai")
        self.assertEqual(payload["model"], "gpt-test")
        self.assertEqual(payload["prompt_version"], STYLE_ENRICHMENT_PROMPT_VERSION)
        self.assertEqual(payload["schema_version"], STYLE_ENRICHMENT_SCHEMA_VERSION)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertEqual(payload["write_status"], "written")

    def test_failed_validation_metric_tags_keep_validation_and_write_status(self) -> None:
        payload = build_style_enrichment_run_event_payload(
            style_id=42,
            source_page_id=101,
            provider="openai",
            model_name="gpt-test",
            status="failed_validation",
            attempts=3,
            did_write=False,
            dry_run=False,
            error_class="ValidationError",
            error_message="payload did not match schema",
        )
        metric = build_style_enrichment_run_metric_payload(payload)

        self.assertFalse(payload["success"])
        self.assertEqual(payload["validation_status"], "failed")
        self.assertEqual(payload["write_status"], "not_written")
        self.assertEqual(metric["metric_name"], "style_enrichment_runs_total")
        self.assertEqual(metric["value"], 1)
        self.assertEqual(metric["tags"]["status"], "failed_validation")
        self.assertEqual(metric["tags"]["validation_status"], "failed")
        self.assertEqual(metric["tags"]["write_status"], "not_written")

    def test_batch_metrics_payload_reports_counts_and_success_rate(self) -> None:
        payload = build_style_enrichment_batch_metrics_payload(
            selected_count=10,
            processed_count=8,
            succeeded_count=6,
            failed_count=2,
            skipped_existing_count=2,
            dry_run=False,
            overwrite_existing=False,
        )

        self.assertEqual(payload["selected_count"], 10)
        self.assertEqual(payload["processed_count"], 8)
        self.assertEqual(payload["succeeded_count"], 6)
        self.assertEqual(payload["failed_count"], 2)
        self.assertEqual(payload["skipped_existing_count"], 2)
        self.assertEqual(payload["success_rate"], 0.75)


if __name__ == "__main__":
    unittest.main()
