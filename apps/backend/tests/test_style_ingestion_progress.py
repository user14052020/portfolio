import io
import json
import unittest
from datetime import datetime, timezone

from scripts.run_style_ingestion import build_cli_progress_reporter


class StyleIngestionProgressReporterTests(unittest.TestCase):
    def test_cli_progress_reporter_writes_json_line_to_stderr_stream(self) -> None:
        stream = io.StringIO()
        reporter = build_cli_progress_reporter(stream=stream)

        reporter(
            "worker_idle",
            {
                "source_name": "aesthetics_wiki",
                "claimable_jobs": 0,
                "next_available_at": datetime(2026, 4, 12, 10, 15, tzinfo=timezone.utc),
            },
        )

        lines = [line for line in stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)

        payload = json.loads(lines[0])
        self.assertEqual(payload["kind"], "style_ingestion_event")
        self.assertEqual(payload["event"], "worker_idle")
        self.assertEqual(payload["source_name"], "aesthetics_wiki")
        self.assertEqual(payload["claimable_jobs"], 0)
        self.assertEqual(payload["next_available_at"], "2026-04-12T10:15:00+00:00")
        self.assertIn("ts", payload)
