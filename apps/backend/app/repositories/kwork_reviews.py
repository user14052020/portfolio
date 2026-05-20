from collections.abc import Iterable

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KworkReview
from app.repositories.base import BaseRepository


class KworkReviewsRepository(BaseRepository[KworkReview]):
    def __init__(self) -> None:
        super().__init__(KworkReview)

    def _build_list_statement(self, *, only_published: bool):
        statement = select(KworkReview).order_by(KworkReview.sort_order.asc(), KworkReview.reviewed_at.desc())
        if only_published:
            statement = statement.where(KworkReview.is_published.is_(True))
        return statement

    async def list_reviews(self, session: AsyncSession, *, only_published: bool) -> list[KworkReview]:
        statement = self._build_list_statement(only_published=only_published)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def list_reviews_page(
        self,
        session: AsyncSession,
        *,
        only_published: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[KworkReview], int]:
        statement = self._build_list_statement(only_published=only_published)
        count_statement = select(func.count()).select_from(KworkReview)
        if only_published:
            count_statement = count_statement.where(KworkReview.is_published.is_(True))
        total = int(await session.scalar(count_statement) or 0)
        result = await session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def replace_reviews(
        self,
        session: AsyncSession,
        reviews: Iterable[dict],
    ) -> list[KworkReview]:
        await session.execute(sa.delete(KworkReview))
        instances = [KworkReview(**review) for review in reviews]
        session.add_all(instances)
        await session.flush()
        return instances

    async def upsert_reviews(
        self,
        session: AsyncSession,
        reviews: Iterable[dict],
    ) -> list[KworkReview]:
        instances: list[KworkReview] = []
        for review in reviews:
            existing = await session.scalar(
                select(KworkReview).where(KworkReview.external_id == review["external_id"])
            )
            if existing is None:
                existing = KworkReview(**review)
                session.add(existing)
            else:
                for field, value in review.items():
                    setattr(existing, field, value)
            instances.append(existing)
        await session.flush()
        return instances


kwork_reviews_repository = KworkReviewsRepository()
