from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import GenerationJob, User
from app.models.enums import GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.schemas.generation_job import GenerationJobCreate, GenerationJobRead
from app.services.generation import QueueRefreshCooldownError, generation_service


router = APIRouter(prefix="/generation-jobs", tags=["generation-jobs"])
settings = get_settings()
ACTIVE_GENERATION_STATUSES = {
    GenerationStatus.PENDING,
    GenerationStatus.QUEUED,
    GenerationStatus.RUNNING,
}
ACTIVE_JOB_READ_SYNC_GRACE_MULTIPLIER = 2


def should_sync_generation_job_on_read(job: GenerationJob) -> bool:
    if job.status not in ACTIVE_GENERATION_STATUSES:
        return False

    if not settings.enable_generation_job_poller:
        return True

    reference_timestamp = job.updated_at or job.started_at or job.created_at
    if reference_timestamp is None:
        return True

    stale_after = timedelta(
        seconds=max(settings.generation_job_poll_interval_seconds, 1) * ACTIVE_JOB_READ_SYNC_GRACE_MULTIPLIER
    )
    return datetime.now(UTC) - reference_timestamp >= stale_after


@router.post("/", response_model=GenerationJobRead, status_code=status.HTTP_201_CREATED)
async def create_generation_job(
    payload: GenerationJobCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_service.create_and_submit(session, payload)
    await session.commit()
    return job


@router.get("/", response_model=list[GenerationJobRead])
async def list_generation_jobs(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GenerationJob]:
    await generation_service.sync_active_jobs(session)
    await session.commit()
    jobs = await generation_jobs_repository.list_jobs(session)
    return [await generation_service.enrich_job_runtime(session, job) for job in jobs]


@router.get("/session/{session_id}", response_model=list[GenerationJobRead])
async def list_generation_jobs_by_session(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GenerationJob]:
    await generation_service.sync_active_jobs(session)
    await session.commit()
    jobs = await generation_jobs_repository.list_jobs(session, session_id=session_id)
    return [await generation_service.enrich_job_runtime(session, job) for job in jobs]


@router.get("/{public_id}", response_model=GenerationJobRead)
async def get_generation_job(
    public_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(session, public_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    if should_sync_generation_job_on_read(job):
        if job.status == GenerationStatus.PENDING:
            await generation_service.sync_active_jobs(session)
            job = await generation_jobs_repository.get_by_public_id(session, public_id) or job
        else:
            job = await generation_service.sync_job_status(session, job)
        await session.commit()
    return await generation_service.enrich_job_runtime(session, job)


@router.post("/{public_id}/refresh-queue", response_model=GenerationJobRead)
async def refresh_generation_job_queue(
    public_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(session, public_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    try:
        job = await generation_service.refresh_pending_job_queue_position(session, job)
    except QueueRefreshCooldownError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "generation_queue_refresh_cooldown",
                "message": "Queue position can only be refreshed once per minute.",
                "retry_after_seconds": exc.retry_after_seconds,
                "next_available_at": exc.next_available_at.isoformat(),
            },
        ) from exc

    await session.commit()
    return job


@router.post("/{public_id}/cancel", response_model=GenerationJobRead)
async def cancel_generation_job(
    public_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(session, public_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    actor = current_user.email or f"user:{current_user.id}"
    job = await generation_service.cancel_job(session, job, actor=actor)
    await session.commit()
    return job


@router.delete("/{public_id}", response_model=GenerationJobRead)
async def delete_generation_job(
    public_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(session, public_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    actor = current_user.email or f"user:{current_user.id}"
    job = await generation_service.delete_job(session, job, actor=actor)
    await session.commit()
    return job
