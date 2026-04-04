from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.db.session import get_db_session
from app.models import User
from app.models.enums import RoleCode


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    result = await session.execute(
        select(User).options(selectinload(User.role)).where(User.id == int(payload["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_current_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    result = await session.execute(
        select(User).options(selectinload(User.role)).where(User.id == int(payload["sub"]))
    )
    return result.scalar_one_or_none()


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role.name != RoleCode.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

