from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair
from app.schemas.user import UserRead
from app.services.auth import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_db_session)]) -> TokenPair:
    user = await auth_service.authenticate_user(session, payload.email, payload.password)
    return auth_service.create_token_pair(user)


@router.post("/refresh")
async def refresh_token(payload: RefreshTokenRequest) -> dict[str, str]:
    return {"access_token": auth_service.refresh_access_token(payload.refresh_token), "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user

