from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StylistStyleExposure
from app.repositories.base import BaseRepository


class StylistStyleExposuresRepository(BaseRepository[StylistStyleExposure]):
    def __init__(self) -> None:
        super().__init__(StylistStyleExposure)

    async def list_for_session_day(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        shown_on: date,
    ) -> list[StylistStyleExposure]:
        result = await session.execute(
            select(StylistStyleExposure).where(
                StylistStyleExposure.session_id == session_id,
                StylistStyleExposure.shown_on == shown_on,
            )
        )
        return list(result.scalars().all())

    async def get_for_session_day_and_style(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        style_direction_id: int,
        shown_on: date,
    ) -> StylistStyleExposure | None:
        result = await session.execute(
            select(StylistStyleExposure).where(
                StylistStyleExposure.session_id == session_id,
                StylistStyleExposure.style_direction_id == style_direction_id,
                StylistStyleExposure.shown_on == shown_on,
            )
        )
        return result.scalar_one_or_none()


stylist_style_exposures_repository = StylistStyleExposuresRepository()
