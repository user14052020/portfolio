from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import StylistChatSession, StylistSessionState, User
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.stylist_chat_sessions import stylist_chat_sessions_repository
from app.repositories.stylist_session_states import stylist_session_states_repository
from app.schemas.admin_chat_sessions import (
    AdminChatSessionDetails,
    AdminChatSessionsPage,
    AdminChatSessionStateSnapshot,
    AdminChatSessionSummary,
)
from app.services.chat_retention import chat_retention_service
from app.services.generation import generation_service


router = APIRouter(prefix="/admin/chats", tags=["admin-chats"])


@router.get("/", response_model=AdminChatSessionsPage)
async def list_admin_chat_sessions(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = Query(None, max_length=120),
) -> AdminChatSessionsPage:
    retention_cutoff = chat_retention_service.cutoff()
    sessions = await stylist_chat_sessions_repository.list_sessions(
        session,
        offset=offset,
        limit=limit,
        query=q,
        active_from=retention_cutoff,
    )
    total = await stylist_chat_sessions_repository.count_sessions(
        session,
        query=q,
        active_from=retention_cutoff,
    )
    return AdminChatSessionsPage(
        items=[_build_session_summary(item) for item in sessions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{session_id}", response_model=AdminChatSessionDetails)
async def get_admin_chat_session_details(
    session_id: str,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminChatSessionDetails:
    chat_session = await stylist_chat_sessions_repository.get_by_session_id(session, session_id)
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    retention_cutoff = chat_retention_service.cutoff()
    session_activity_at = chat_session.last_message_at or chat_session.updated_at
    if session_activity_at < retention_cutoff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    messages = await chat_messages_repository.list_by_session(
        session,
        session_id,
        limit=100,
        created_at_from=retention_cutoff,
    )
    generation_jobs = await generation_jobs_repository.list_jobs(
        session,
        session_id=session_id,
        include_deleted=True,
        created_at_from=retention_cutoff,
    )
    enriched_generation_jobs = [
        await generation_service.enrich_job_runtime(session, job)
        for job in generation_jobs
    ]
    state = await stylist_session_states_repository.get_by_session_id(session, session_id)

    return AdminChatSessionDetails(
        session=_build_session_summary(chat_session),
        messages=messages,
        generation_jobs=enriched_generation_jobs,
        state=_build_state_snapshot(state),
    )


def _build_session_summary(session: StylistChatSession) -> AdminChatSessionSummary:
    return AdminChatSessionSummary(
        id=session.id,
        session_id=session.session_id,
        started_at=session.started_at,
        last_message_at=session.last_message_at,
        message_count=session.message_count,
        locale=session.locale,
        client_ip=session.client_ip,
        client_user_agent=session.client_user_agent,
        client_user_agent_short=_short_user_agent(session.client_user_agent),
        last_active_mode=session.last_active_mode,
        last_decision_type=session.last_decision_type,
        metadata_json=dict(session.metadata_json or {}),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _build_state_snapshot(state: StylistSessionState | None) -> AdminChatSessionStateSnapshot | None:
    if state is None:
        return None
    return AdminChatSessionStateSnapshot(
        id=state.id,
        session_id=state.session_id,
        active_intent=state.active_intent,
        state_payload=dict(state.state_payload or {}),
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _short_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    cleaned = " ".join(user_agent.split())
    if len(cleaned) <= 96:
        return cleaned
    return f"{cleaned[:93]}..."
