from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import (
    Style,
    StyleIngestJob,
    StyleIngestRun,
    StyleProfile,
    StyleRelation,
    StyleSourcePage,
    StyleSourcePageVersion,
    StyleTaxonomyLink,
    StyleTrait,
    User,
)
from app.schemas.style_ingestion_admin import (
    ParserAdminCommandsRead,
    ParserAdminOverviewRead,
    ParserAdminProcessRead,
    ParserAdminRecentRunRead,
    ParserAdminStartRequest,
    ParserAdminStatsRead,
)
from app.services.style_ingestion_admin import style_ingestion_admin_service


router = APIRouter(prefix="/style-ingestion-admin", tags=["style-ingestion-admin"])


async def _count_rows(session: AsyncSession, model: type[object]) -> int:
    return int((await session.scalar(select(func.count()).select_from(model))) or 0)


async def _build_overview(
    session: AsyncSession,
    *,
    source_name: str = "aesthetics_wiki",
    limit: int = 50,
    worker_max_jobs: int = 50,
    title_contains: str | None = None,
) -> ParserAdminOverviewRead:
    process = style_ingestion_admin_service.snapshot()
    commands = style_ingestion_admin_service.build_commands(
        source_name=source_name,
        limit=limit,
        worker_max_jobs=worker_max_jobs,
        title_contains=title_contains,
    )

    job_status_counts = {
        status_name: int(total)
        for status_name, total in (
            await session.execute(select(StyleIngestJob.status, func.count()).group_by(StyleIngestJob.status))
        ).all()
    }
    run_status_counts = {
        status_name: int(total)
        for status_name, total in (
            await session.execute(select(StyleIngestRun.run_status, func.count()).group_by(StyleIngestRun.run_status))
        ).all()
    }
    recent_runs = (
        await session.execute(
            select(StyleIngestRun).order_by(StyleIngestRun.started_at.desc(), StyleIngestRun.id.desc()).limit(6)
        )
    ).scalars().all()

    return ParserAdminOverviewRead(
        process=ParserAdminProcessRead(
            state=process.state,
            pid=process.pid,
            started_at=process.started_at,
            stop_requested_at=process.stop_requested_at,
            last_exit_code=process.last_exit_code,
            last_error=process.last_error,
            command=process.command,
            log_path=process.log_path,
            pid_file_path=process.pid_file_path,
        ),
        commands=ParserAdminCommandsRead(**commands),
        stats=ParserAdminStatsRead(
            styles_total=await _count_rows(session, Style),
            source_pages_total=await _count_rows(session, StyleSourcePage),
            source_page_versions_total=await _count_rows(session, StyleSourcePageVersion),
            style_profiles_total=await _count_rows(session, StyleProfile),
            style_traits_total=await _count_rows(session, StyleTrait),
            taxonomy_links_total=await _count_rows(session, StyleTaxonomyLink),
            relations_total=await _count_rows(session, StyleRelation),
            jobs_total=await _count_rows(session, StyleIngestJob),
            jobs_queued=job_status_counts.get("queued", 0),
            jobs_running=job_status_counts.get("running", 0),
            jobs_succeeded=job_status_counts.get("succeeded", 0),
            jobs_soft_failed=job_status_counts.get("soft_failed", 0),
            jobs_hard_failed=job_status_counts.get("hard_failed", 0),
            jobs_cooldown_deferred=job_status_counts.get("cooldown_deferred", 0),
            runs_total=await _count_rows(session, StyleIngestRun),
            runs_completed=run_status_counts.get("completed", 0),
            runs_failed=run_status_counts.get("failed", 0),
            runs_completed_with_failures=run_status_counts.get("completed_with_failures", 0),
            runs_aborted=run_status_counts.get("aborted", 0),
        ),
        recent_runs=[
            ParserAdminRecentRunRead(
                run_id=run.id,
                source_name=run.source_name,
                source_url=run.source_url,
                run_status=run.run_status,
                styles_seen=run.styles_seen,
                styles_created=run.styles_created,
                styles_updated=run.styles_updated,
                styles_failed=run.styles_failed,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
            for run in recent_runs
        ],
        log_tail=style_ingestion_admin_service.read_log_tail(lines=40),
    )


@router.get("/overview", response_model=ParserAdminOverviewRead)
async def get_style_ingestion_admin_overview(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ParserAdminOverviewRead:
    return await _build_overview(session)


@router.post("/start", response_model=ParserAdminOverviewRead)
async def start_style_ingestion_worker(
    payload: ParserAdminStartRequest,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ParserAdminOverviewRead:
    try:
        style_ingestion_admin_service.start(
            source_name=payload.source_name,
            limit=payload.limit,
            worker_max_jobs=payload.worker_max_jobs,
            title_contains=payload.title_contains,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return await _build_overview(
        session,
        source_name=payload.source_name,
        limit=payload.limit,
        worker_max_jobs=payload.worker_max_jobs,
        title_contains=payload.title_contains,
    )


@router.post("/stop", response_model=ParserAdminOverviewRead)
async def stop_style_ingestion_worker(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ParserAdminOverviewRead:
    style_ingestion_admin_service.stop()
    return await _build_overview(session)
