from sqlalchemy import select
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

    async def list_jobs(self, session: AsyncSession, session_id: str | None = None) -> list[GenerationJob]:
        statement = select(GenerationJob).options(joinedload(GenerationJob.input_asset)).order_by(
            GenerationJob.created_at.desc()
        )
        if session_id:
            statement = statement.where(GenerationJob.session_id == session_id)
        result = await session.execute(statement)
        return list(result.scalars().unique().all())

    async def list_active_jobs(self, session: AsyncSession) -> list[GenerationJob]:
        result = await session.execute(
            select(GenerationJob).where(
                GenerationJob.status.in_([GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING])
            )
        )
        return list(result.scalars().all())


generation_jobs_repository = GenerationJobsRepository()

