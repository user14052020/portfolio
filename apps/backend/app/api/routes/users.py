from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db_session
from app.models import User
from app.repositories.users import users_repository
from app.schemas.user import UserPasswordChangeRequest, UserRead


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


@router.put("/me/password", response_model=UserRead)
async def change_my_password(
    payload: UserPasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    user_email = current_user.email
    current_user.hashed_password = get_password_hash(payload.new_password)
    session.add(current_user)
    await session.flush()
    await session.commit()
    updated_user = await users_repository.get_by_email(session, user_email)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user
