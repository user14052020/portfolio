from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db_session
from app.models import User
from app.repositories.users import users_repository
from app.schemas.user import UserRead


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/", response_model=list[UserRead])
async def list_users(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[User]:
    return await users_repository.list_with_roles(session)

