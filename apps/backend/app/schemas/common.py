from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


DataT = TypeVar("DataT")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMModel):
    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: list[DataT]
    total: int

