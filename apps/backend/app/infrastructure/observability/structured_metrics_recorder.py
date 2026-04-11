import logging
from typing import Any

from app.application.stylist_chat.contracts.ports import MetricsRecorder


logger = logging.getLogger(__name__)


class StructuredMetricsRecorder(MetricsRecorder):
    async def increment(
        self,
        metric_name: str,
        *,
        value: int = 1,
        tags: dict[str, Any] | None = None,
    ) -> None:
        logger.info("metric.counter | %s | %s", metric_name, {"value": value, "tags": tags or {}})

    async def observe(
        self,
        metric_name: str,
        *,
        value: float,
        tags: dict[str, Any] | None = None,
    ) -> None:
        logger.info("metric.observe | %s | %s", metric_name, {"value": value, "tags": tags or {}})
