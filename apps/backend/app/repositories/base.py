from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, session: AsyncSession, entity_id: int) -> ModelType | None:
        result = await session.execute(select(self.model).where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 20,
        query: Select[Any] | None = None,
    ) -> Sequence[ModelType]:
        statement = query or select(self.model)
        statement = statement.offset(offset).limit(limit)
        result = await session.execute(statement)
        return result.scalars().unique().all()

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> ModelType:
        instance = self.model(**data)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def update(self, session: AsyncSession, instance: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, instance: ModelType) -> None:
        await session.delete(instance)
        await session.flush()

