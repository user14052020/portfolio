from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user, require_admin
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import GenerationJob, User
from app.models.enums import GenerationStatus
from app.domain.usage_access_policy import RequestedAction
from app.infrastructure.observability.runtime_policy_observability import RuntimePolicyObservability
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate, GenerationJobRead
from app.services.chat_retention import chat_retention_service
from app.services.client_request_meta import client_request_meta_resolver
from app.services.generation import QueueRefreshCooldownError, generation_service
from app.services.usage_access_policy import UsageAccessPolicyService
import httpx
from fastapi import Query
from fastapi.responses import Response

router = APIRouter(prefix="/generation-jobs", tags=["generation-jobs"])
settings = get_settings()
usage_access_policy_service = UsageAccessPolicyService()
runtime_policy_observability = RuntimePolicyObservability()
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
    return datetime.now(timezone.utc) - reference_timestamp >= stale_after


@router.post("/", response_model=GenerationJobRead, status_code=status.HTTP_201_CREATED)
async def create_generation_job(
    request: Request,
    payload: GenerationJobCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> GenerationJob:
    request_meta = client_request_meta_resolver.resolve(request)
    try:
        subject = usage_access_policy_service.build_subject(
            current_user=current_user,
            session_id=payload.session_id,
            metadata=payload.metadata,
            request_meta=request_meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_decision = await usage_access_policy_service.evaluate(
        session,
        subject=subject,
        action=RequestedAction(action_type="generation"),
    )
    await runtime_policy_observability.record_usage_access_decision(
        subject=subject,
        action_type="generation",
        decision=access_decision,
        surface="generation_jobs_api",
    )
    if not access_decision.is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": access_decision.denial_reason,
                "message": "Daily generation limit reached for this subject.",
                "remaining_generations": access_decision.remaining_generations,
                "remaining_chat_seconds": access_decision.remaining_chat_seconds,
            },
        )

    if payload.input_asset_id is not None:
        input_asset = await uploads_repository.get(session, payload.input_asset_id)
        if input_asset is None or chat_retention_service.is_expired(input_asset.created_at):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded asset not found")

    payload = payload.model_copy(
        update={
            "metadata": {
                **(payload.metadata if isinstance(payload.metadata, dict) else {}),
                **usage_access_policy_service.subject_to_metadata(subject),
            },
            **request_meta.model_fields(),
        }
    )
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
    jobs = await generation_jobs_repository.list_jobs(
        session,
        created_at_from=chat_retention_service.cutoff(),
    )
    return [await generation_service.enrich_job_runtime(session, job) for job in jobs]


@router.get("/session/{session_id}", response_model=list[GenerationJobRead])
async def list_generation_jobs_by_session(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GenerationJob]:
    await generation_service.sync_active_jobs(session)
    await session.commit()
    jobs = await generation_jobs_repository.list_jobs(
        session,
        session_id=session_id,
        created_at_from=chat_retention_service.cutoff(),
    )
    return [await generation_service.enrich_job_runtime(session, job) for job in jobs]

@router.get("/image-proxy")
async def proxy_generation_result_image(
    filename: str = Query(...),
    subfolder: str = Query(""),
    file_type: str = Query("output", alias="type"),
) -> Response:
    comfy_base = settings.comfyui_base_url.rstrip("/")
    url = f"{comfy_base}/view"

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.get(
            url,
            params={
                "filename": filename,
                "subfolder": subfolder,
                "type": file_type,
            },
        )

    content_type = upstream.headers.get("content-type", "image/png")
    return Response(
        content=upstream.content,
        media_type=content_type,
        status_code=upstream.status_code,
    )

@router.get("/{public_id}", response_model=GenerationJobRead)
async def get_generation_job(
    public_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(
        session,
        public_id,
        created_at_from=chat_retention_service.cutoff(),
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    if should_sync_generation_job_on_read(job):
        if job.status == GenerationStatus.PENDING:
            await generation_service.sync_active_jobs(session)
            job = (
                await generation_jobs_repository.get_by_public_id(
                    session,
                    public_id,
                    created_at_from=chat_retention_service.cutoff(),
                )
                or job
            )
        else:
            job = await generation_service.sync_job_status(session, job)
        await session.commit()
    return await generation_service.enrich_job_runtime(session, job)


@router.post("/{public_id}/refresh-queue", response_model=GenerationJobRead)
async def refresh_generation_job_queue(
    public_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(
        session,
        public_id,
        created_at_from=chat_retention_service.cutoff(),
    )
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
