from typing import Protocol

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.domain.chat_context import ChatModeContext


class ChatModeHandler(Protocol):
    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        ...
