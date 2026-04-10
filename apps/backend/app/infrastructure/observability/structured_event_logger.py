import logging
from typing import Any

from app.application.stylist_chat.contracts.ports import EventLogger


logger = logging.getLogger(__name__)


class StructuredEventLogger(EventLogger):
    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        logger.info("%s | %s", event_name, payload)
