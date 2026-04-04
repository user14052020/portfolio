from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.stylist import ChatMessageRead, StylistMessageRequest, StylistMessageResponse
from app.services.stylist_ai import stylist_service


router = APIRouter(prefix="/stylist-chat", tags=["stylist-chat"])


@router.post("/message", response_model=StylistMessageResponse)
async def send_stylist_message(
    payload: StylistMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StylistMessageResponse:
    result = await stylist_service.process_message(session, payload)
    await session.commit()
    return StylistMessageResponse.model_validate(result)


@router.get("/history/{session_id}", response_model=list[ChatMessageRead])
async def get_chat_history(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ChatMessageRead]:
    return await stylist_service.get_history(session, session_id)
