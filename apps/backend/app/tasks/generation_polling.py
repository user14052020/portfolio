from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.generation_jobs import generation_jobs_repository
from app.services.generation import generation_service


async def refresh_active_generation_jobs(session: AsyncSession) -> None:
    jobs = await generation_jobs_repository.list_active_jobs(session)
    for job in jobs:
        await generation_service.sync_job_status(session, job)

