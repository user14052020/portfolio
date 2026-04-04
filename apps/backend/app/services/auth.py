from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models import User
from app.repositories.users import users_repository
from app.schemas.auth import TokenPair


class AuthService:
    async def authenticate_user(self, session: AsyncSession, email: str, password: str) -> User:
        user = await users_repository.get_by_email(session, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        return user

    def create_token_pair(self, user: User) -> TokenPair:
        subject = str(user.id)
        return TokenPair(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return create_access_token(payload["sub"])


auth_service = AuthService()

