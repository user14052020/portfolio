import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.generation_jobs import generation_jobs_repository
from app.services.generation import generation_service


async def refresh_active_generation_jobs(session: AsyncSession) -> None:
    jobs = await generation_jobs_repository.list_active_jobs(session)
    for job in jobs:
        await generation_service.sync_job_status(session, job)


logger = logging.getLogger(__name__)


async def run_generation_job_poller(stop_event: asyncio.Event) -> None:
    settings = get_settings()

    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                try:
                    await generation_service.sync_active_jobs(session)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        except Exception:
            logger.exception("Generation job poller iteration failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.generation_job_poll_interval_seconds)
        except asyncio.TimeoutError:
            continue
