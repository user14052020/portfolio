from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StylistSessionState
from app.repositories.base import BaseRepository


class StylistSessionStatesRepository(BaseRepository[StylistSessionState]):
    def __init__(self) -> None:
        super().__init__(StylistSessionState)

    async def get_by_session_id(self, session: AsyncSession, session_id: str) -> StylistSessionState | None:
        result = await session.execute(
            select(StylistSessionState).where(StylistSessionState.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def delete_older_than(self, session: AsyncSession, cutoff: datetime) -> int:
        result = await session.execute(delete(StylistSessionState).where(StylistSessionState.updated_at < cutoff))
        await session.flush()
        return int(result.rowcount or 0)


stylist_session_states_repository = StylistSessionStatesRepository()
