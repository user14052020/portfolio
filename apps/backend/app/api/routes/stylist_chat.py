from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.domain.chat_context import ChatModeContext
from app.schemas.stylist import (
    ChatHistoryPageRead,
    StylistMessageRequest,
    StylistMessageResponse,
)
from app.services.stylist_conversational import stylist_service


router = APIRouter(prefix="/stylist-chat", tags=["stylist-chat"])


@router.post("/message", response_model=StylistMessageResponse)
async def send_stylist_message(
    payload: StylistMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StylistMessageResponse:
    result = await stylist_service.process_message(session, payload)
    await session.commit()
    return StylistMessageResponse.model_validate(result)


@router.get("/context/{session_id}", response_model=ChatModeContext)
async def get_chat_context(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatModeContext:
    context = await stylist_service.get_context(session, session_id)
    return ChatModeContext.model_validate(context)


@router.get("/history/{session_id}", response_model=ChatHistoryPageRead)
async def get_chat_history(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(5, ge=1, le=20),
    before_message_id: int | None = Query(None, ge=1),
) -> ChatHistoryPageRead:
    result = await stylist_service.get_history_page(
        session,
        session_id,
        limit=limit,
        before_message_id=before_message_id,
    )
    return ChatHistoryPageRead.model_validate(result)
