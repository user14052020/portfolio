from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.base import BaseRepository


class UsersRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).options(selectinload(User.role)).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_with_roles(self, session: AsyncSession) -> list[User]:
        result = await session.execute(select(User).options(selectinload(User.role)).order_by(User.created_at.desc()))
        return list(result.scalars().unique().all())


users_repository = UsersRepository()

