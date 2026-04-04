from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, GenerationJob
from app.models.enums import ChatMessageRole
from app.repositories.base import BaseRepository


class ChatMessagesRepository(BaseRepository[ChatMessage]):
    def __init__(self) -> None:
        super().__init__(ChatMessage)

    async def list_by_session(self, session: AsyncSession, session_id: str, limit: int = 50) -> list[ChatMessage]:
        result = await session.execute(
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.uploaded_asset),
                joinedload(ChatMessage.generation_job).joinedload(GenerationJob.input_asset),
            )
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        items = list(result.scalars().all())
        items.reverse()
        return items

    async def get_with_relations(self, session: AsyncSession, message_id: int) -> ChatMessage | None:
        result = await session.execute(
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.uploaded_asset),
                joinedload(ChatMessage.generation_job).joinedload(GenerationJob.input_asset),
            )
            .where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_user_message(self, session: AsyncSession, session_id: str) -> ChatMessage | None:
        result = await session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == ChatMessageRole.USER,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def trim_session(self, session: AsyncSession, session_id: str, keep_latest: int = 50) -> None:
        overflow_ids = (
            select(ChatMessage.id)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .offset(keep_latest)
        )
        await session.execute(delete(ChatMessage).where(ChatMessage.id.in_(overflow_ids)))
        await session.flush()


chat_messages_repository = ChatMessagesRepository()
