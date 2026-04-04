from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContactRequest
from app.repositories.base import BaseRepository


class ContactRequestsRepository(BaseRepository[ContactRequest]):
    def __init__(self) -> None:
        super().__init__(ContactRequest)

    async def list_requests(self, session: AsyncSession) -> list[ContactRequest]:
        result = await session.execute(select(ContactRequest).order_by(ContactRequest.created_at.desc()))
        return list(result.scalars().all())


contact_requests_repository = ContactRequestsRepository()

