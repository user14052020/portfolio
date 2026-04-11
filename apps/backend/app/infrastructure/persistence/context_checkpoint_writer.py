from app.application.stylist_chat.contracts.ports import ContextCheckpointWriter
from app.domain.chat_context import ChatModeContext
from app.infrastructure.persistence.stylist_chat_context_store import SessionChatContextStore


class SessionContextCheckpointWriter(ContextCheckpointWriter):
    def __init__(self, context_store: SessionChatContextStore) -> None:
        self.context_store = context_store

    async def save_checkpoint(self, *, session_id: str, context: ChatModeContext) -> None:
        record, _ = await self.context_store.load(session_id)
        await self.context_store.save(
            session_id=session_id,
            context=context,
            record=record,
        )
