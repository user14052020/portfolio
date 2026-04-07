import random
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StyleDirection, StylistStyleExposure
from app.repositories.base import BaseRepository


class StyleDirectionsRepository(BaseRepository[StyleDirection]):
    def __init__(self) -> None:
        super().__init__(StyleDirection)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> StyleDirection | None:
        result = await session.execute(select(StyleDirection).where(StyleDirection.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(self, session: AsyncSession) -> list[StyleDirection]:
        result = await session.execute(
            select(StyleDirection)
            .where(StyleDirection.is_active.is_(True))
            .order_by(StyleDirection.sort_order.asc(), StyleDirection.id.asc())
        )
        return list(result.scalars().all())

    async def list_active_not_shown_today(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        shown_on: date,
    ) -> list[StyleDirection]:
        shown_subquery = (
            select(StylistStyleExposure.style_direction_id)
            .where(
                StylistStyleExposure.session_id == session_id,
                StylistStyleExposure.shown_on == shown_on,
            )
            .subquery()
        )
        result = await session.execute(
            select(StyleDirection)
            .where(
                StyleDirection.is_active.is_(True),
                StyleDirection.id.not_in(select(shown_subquery.c.style_direction_id)),
            )
            .order_by(StyleDirection.sort_order.asc(), StyleDirection.id.asc())
        )
        return list(result.scalars().all())

    async def pick_random_active_style(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        shown_on: date,
    ) -> StyleDirection | None:
        candidates = await self.list_active_not_shown_today(session, session_id=session_id, shown_on=shown_on)
        if not candidates:
            candidates = await self.list_active(session)
        if not candidates:
            return None

        weights = [max(candidate.selection_weight, 1) for candidate in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]


style_directions_repository = StyleDirectionsRepository()
