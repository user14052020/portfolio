from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_context import ChatModeContext
from app.models import StylistSessionState
from app.repositories.stylist_session_states import stylist_session_states_repository
from app.services.chat_retention import chat_retention_service


class ChatContextStore:
    async def load(self, session: AsyncSession, session_id: str) -> tuple[StylistSessionState | None, ChatModeContext]:
        record = await stylist_session_states_repository.get_by_session_id(session, session_id)
        if record is None or chat_retention_service.is_expired(record.updated_at):
            return None, ChatModeContext()

        try:
            context = ChatModeContext.model_validate(record.state_payload or {})
        except ValidationError:
            context = ChatModeContext()
        return record, context

    async def save(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        context: ChatModeContext,
        record: StylistSessionState | None,
    ) -> StylistSessionState:
        payload = context.model_dump(mode="json")
        if record is None:
            return await stylist_session_states_repository.create(
                session,
                {
                    "session_id": session_id,
                    "active_intent": context.active_mode.value,
                    "state_payload": payload,
                },
            )

        return await stylist_session_states_repository.update(
            session,
            record,
            {
                "active_intent": context.active_mode.value,
                "state_payload": payload,
            },
        )


chat_context_store = ChatContextStore()
