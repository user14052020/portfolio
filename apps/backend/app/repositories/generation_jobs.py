from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationJob
from app.models.enums import GenerationStatus
from app.repositories.base import BaseRepository


class GenerationJobsRepository(BaseRepository[GenerationJob]):
    def __init__(self) -> None:
        super().__init__(GenerationJob)

    async def get_by_public_id(
        self,
        session: AsyncSession,
        public_id: str,
        *,
        created_at_from: datetime | None = None,
    ) -> GenerationJob | None:
        statement = (
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(GenerationJob.public_id == public_id)
        )
        if created_at_from is not None:
            statement = statement.where(GenerationJob.created_at >= created_at_from)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        session: AsyncSession,
        session_id: str | None = None,
        *,
        include_deleted: bool = False,
        created_at_from: datetime | None = None,
    ) -> list[GenerationJob]:
        statement = select(GenerationJob).options(joinedload(GenerationJob.input_asset)).order_by(
            GenerationJob.created_at.desc()
        )
        if session_id:
            statement = statement.where(GenerationJob.session_id == session_id)
        if not include_deleted:
            statement = statement.where(GenerationJob.deleted_at.is_(None))
        if created_at_from is not None:
            statement = statement.where(GenerationJob.created_at >= created_at_from)
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
        *,
        created_at_from: datetime | None = None,
    ) -> GenerationJob | None:
        statement = (
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
        if created_at_from is not None:
            statement = statement.where(GenerationJob.created_at >= created_at_from)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def list_older_than(self, session: AsyncSession, cutoff: datetime) -> list[GenerationJob]:
        result = await session.execute(
            select(GenerationJob)
            .options(joinedload(GenerationJob.input_asset))
            .where(GenerationJob.created_at < cutoff)
        )
        return list(result.scalars().unique().all())

    async def detach_uploaded_assets(self, session: AsyncSession, uploaded_asset_ids: list[int]) -> int:
        if not uploaded_asset_ids:
            return 0
        result = await session.execute(
            update(GenerationJob)
            .where(GenerationJob.input_asset_id.in_(uploaded_asset_ids))
            .values(input_asset_id=None)
        )
        await session.flush()
        return int(result.rowcount or 0)

    async def delete_by_ids(self, session: AsyncSession, job_ids: list[int]) -> int:
        if not job_ids:
            return 0
        result = await session.execute(delete(GenerationJob).where(GenerationJob.id.in_(job_ids)))
        await session.flush()
        return int(result.rowcount or 0)


generation_jobs_repository = GenerationJobsRepository()
