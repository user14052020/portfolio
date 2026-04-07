from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationJob
from app.models.enums import GenerationStatus
from app.repositories.base import BaseRepository


class GenerationJobsRepository(BaseRepository[GenerationJob]):
    def __init__(self) -> None:
        super().__init__(GenerationJob)

    async def get_by_public_id(self, session: AsyncSession, public_id: str) -> GenerationJob | None:
        result = await session.execute(
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(GenerationJob.public_id == public_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        session: AsyncSession,
        session_id: str | None = None,
        *,
        include_deleted: bool = False,
    ) -> list[GenerationJob]:
        statement = select(GenerationJob).options(joinedload(GenerationJob.input_asset)).order_by(
            GenerationJob.created_at.desc()
        )
        if session_id:
            statement = statement.where(GenerationJob.session_id == session_id)
        if not include_deleted:
            statement = statement.where(GenerationJob.deleted_at.is_(None))
        result = await session.execute(statement)
        return list(result.scalars().unique().all())

    async def list_active_jobs(self, session: AsyncSession) -> list[GenerationJob]:
        result = await session.execute(
            select(GenerationJob).where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.status.in_(
                    [GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING]
                ),
            )
        )
        return list(result.scalars().all())

    async def get_oldest_pending_job(self, session: AsyncSession) -> GenerationJob | None:
        result = await session.execute(
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.status == GenerationStatus.PENDING,
            )
            .order_by(GenerationJob.created_at.asc(), GenerationJob.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_oldest_provider_active_job(self, session: AsyncSession) -> GenerationJob | None:
        result = await session.execute(
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.status.in_([GenerationStatus.QUEUED, GenerationStatus.RUNNING]),
            )
            .order_by(GenerationJob.created_at.asc(), GenerationJob.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_pending_jobs(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.status == GenerationStatus.PENDING,
            )
        )
        return int(result.scalar_one() or 0)

    async def count_pending_jobs_ahead(self, session: AsyncSession, job: GenerationJob) -> int:
        created_at = job.created_at
        result = await session.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.status == GenerationStatus.PENDING,
                or_(
                    GenerationJob.created_at < created_at,
                    and_(GenerationJob.created_at == created_at, GenerationJob.id < job.id),
                ),
            )
        )
        return int(result.scalar_one() or 0)

    async def get_latest_active_by_session(
        self,
        session: AsyncSession,
        session_id: str,
    ) -> GenerationJob | None:
        result = await session.execute(
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(
                GenerationJob.deleted_at.is_(None),
                GenerationJob.session_id == session_id,
                GenerationJob.status.in_(
                    [GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING]
                ),
            )
            .order_by(GenerationJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


generation_jobs_repository = GenerationJobsRepository()
