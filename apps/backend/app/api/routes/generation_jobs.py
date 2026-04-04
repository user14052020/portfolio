from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import GenerationJob, User
from app.repositories.generation_jobs import generation_jobs_repository
from app.schemas.generation_job import GenerationJobCreate, GenerationJobRead
from app.services.generation import generation_service


router = APIRouter(prefix="/generation-jobs", tags=["generation-jobs"])


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
    return await generation_jobs_repository.list_jobs(session)


@router.get("/session/{session_id}", response_model=list[GenerationJobRead])
async def list_generation_jobs_by_session(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GenerationJob]:
    return await generation_jobs_repository.list_jobs(session, session_id=session_id)


@router.get("/{public_id}", response_model=GenerationJobRead)
async def get_generation_job(
    public_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerationJob:
    job = await generation_jobs_repository.get_by_public_id(session, public_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    job = await generation_service.sync_job_status(session, job)
    await session.commit()
    return job

