from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, GenerationJob
from app.models.enums import ChatMessageRole
from app.repositories.base import BaseRepository


class ChatMessagesRepository(BaseRepository[ChatMessage]):
    def __init__(self) -> None:
        super().__init__(ChatMessage)

    async def list_by_session(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 50,
        *,
        created_at_from: datetime | None = None,
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.uploaded_asset),
                joinedload(ChatMessage.generation_job).joinedload(GenerationJob.input_asset),
            )
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        if created_at_from is not None:
            statement = statement.where(ChatMessage.created_at >= created_at_from)

        result = await session.execute(statement)
        items = list(result.scalars().all())
        items.reverse()
        return items

    async def list_page_by_session(
        self,
        session: AsyncSession,
        session_id: str,
        *,
        limit: int = 5,
        before_message_id: int | None = None,
        created_at_from: datetime | None = None,
    ) -> tuple[list[ChatMessage], bool]:
        statement = (
            select(ChatMessage)
            .options(
                joinedload(ChatMessage.uploaded_asset),
                joinedload(ChatMessage.generation_job).joinedload(GenerationJob.input_asset),
            )
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit + 1)
        )
        if before_message_id is not None:
            statement = statement.where(ChatMessage.id < before_message_id)
        if created_at_from is not None:
            statement = statement.where(ChatMessage.created_at >= created_at_from)

        result = await session.execute(statement)
        items = list(result.scalars().all())
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
        items.reverse()
        return items, has_more

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

    async def get_latest_user_message(
        self,
        session: AsyncSession,
        session_id: str,
        *,
        created_at_from: datetime | None = None,
    ) -> ChatMessage | None:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == ChatMessageRole.USER,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        if created_at_from is not None:
            statement = statement.where(ChatMessage.created_at >= created_at_from)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_assistant_message(
        self,
        session: AsyncSession,
        session_id: str,
        *,
        created_at_from: datetime | None = None,
    ) -> ChatMessage | None:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == ChatMessageRole.ASSISTANT,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
        )
        if created_at_from is not None:
            statement = statement.where(ChatMessage.created_at >= created_at_from)

        result = await session.execute(statement)
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

    async def detach_generation_jobs(self, session: AsyncSession, generation_job_ids: list[int]) -> int:
        if not generation_job_ids:
            return 0
        result = await session.execute(
            update(ChatMessage)
            .where(ChatMessage.generation_job_id.in_(generation_job_ids))
            .values(generation_job_id=None)
        )
        await session.flush()
        return int(result.rowcount or 0)

    async def detach_uploaded_assets(self, session: AsyncSession, uploaded_asset_ids: list[int]) -> int:
        if not uploaded_asset_ids:
            return 0
        result = await session.execute(
            update(ChatMessage)
            .where(ChatMessage.uploaded_asset_id.in_(uploaded_asset_ids))
            .values(uploaded_asset_id=None)
        )
        await session.flush()
        return int(result.rowcount or 0)

    async def delete_older_than(self, session: AsyncSession, cutoff: datetime) -> int:
        result = await session.execute(delete(ChatMessage).where(ChatMessage.created_at < cutoff))
        await session.flush()
        return int(result.rowcount or 0)


chat_messages_repository = ChatMessagesRepository()
