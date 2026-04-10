from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.contracts.ports import ChatContextStorePort
from app.domain.chat_context import ChatModeContext
from app.services.chat_context_store import chat_context_store


class SessionChatContextStore(ChatContextStorePort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, session_id: str) -> tuple[Any | None, ChatModeContext]:
        return await chat_context_store.load(self.session, session_id)

    async def save(
        self,
        *,
        session_id: str,
        context: ChatModeContext,
        record: Any | None,
    ) -> Any:
        return await chat_context_store.save(
            self.session,
            session_id=session_id,
            context=context,
            record=record,
        )
