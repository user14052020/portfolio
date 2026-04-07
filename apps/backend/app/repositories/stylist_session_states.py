from sqlalchemy import select
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


stylist_session_states_repository = StylistSessionStatesRepository()
