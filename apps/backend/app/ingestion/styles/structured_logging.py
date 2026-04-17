from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, TextIO


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class StructuredIngestionLogger:
    def __init__(
        self,
        *,
        logger_name: str = "app.ingestion.styles",
        mirror_stream: TextIO | None = None,
    ) -> None:
        self._logger = logging.getLogger(logger_name)
        self._mirror_stream = mirror_stream

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        message = {
            "kind": "style_ingestion_event",
            "ts": datetime.now(UTC).isoformat(),
            "event": event_name,
            **payload,
        }
        serialized = json.dumps(message, ensure_ascii=False, default=_json_default)
        self._logger.info(serialized)
        if self._mirror_stream is not None:
            print(serialized, file=self._mirror_stream, flush=True)

    def as_reporter(self):
        def report(event_name: str, payload: dict[str, Any]) -> None:
            self.emit(event_name, payload)

        return report

