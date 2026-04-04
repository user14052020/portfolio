from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.repositories.base import BaseRepository


class ProjectsRepository(BaseRepository[Project]):
    def __init__(self) -> None:
        super().__init__(Project)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> Project | None:
        result = await session.execute(
            select(Project).options(selectinload(Project.media_items)).where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        session: AsyncSession,
        *,
        only_published: bool,
        q: str | None = None,
        featured_only: bool = False,
    ) -> list[Project]:
        statement = select(Project).options(selectinload(Project.media_items)).order_by(Project.sort_order.asc())
        if only_published:
            statement = statement.where(Project.is_published.is_(True))
        if featured_only:
            statement = statement.where(Project.is_featured.is_(True))
        if q:
            pattern = f"%{q}%"
            statement = statement.where(
                or_(
                    Project.title_ru.ilike(pattern),
                    Project.title_en.ilike(pattern),
                    Project.summary_ru.ilike(pattern),
                    Project.summary_en.ilike(pattern),
                )
            )
        result = await session.execute(statement)
        return list(result.scalars().unique().all())


projects_repository = ProjectsRepository()

