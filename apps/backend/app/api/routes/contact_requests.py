from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import ContactRequest, User
from app.repositories.contact_requests import contact_requests_repository
from app.schemas.contact_request import ContactRequestCreate, ContactRequestRead, ContactRequestUpdate


router = APIRouter(prefix="/contact-requests", tags=["contact-requests"])


@router.post("/", response_model=ContactRequestRead, status_code=status.HTTP_201_CREATED)
async def create_contact_request(
    payload: ContactRequestCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactRequest:
    contact_request = await contact_requests_repository.create(session, payload.model_dump())
    await session.commit()
    return contact_request


@router.get("/", response_model=list[ContactRequestRead])
async def list_contact_requests(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ContactRequest]:
    return await contact_requests_repository.list_requests(session)


@router.patch("/{request_id}", response_model=ContactRequestRead)
async def update_contact_request(
    request_id: int,
    payload: ContactRequestUpdate,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContactRequest:
    contact_request = await contact_requests_repository.get(session, request_id)
    if not contact_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact request not found")
    contact_request = await contact_requests_repository.update(session, contact_request, payload.model_dump())
    await session.commit()
    return contact_request

