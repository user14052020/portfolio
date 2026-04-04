from pydantic import BaseModel, EmailStr

from app.models.enums import ContactRequestStatus
from app.schemas.common import TimestampedRead


class ContactRequestCreate(BaseModel):
    name: str
    email: EmailStr
    message: str
    locale: str = "en"
    source_page: str | None = None


class ContactRequestUpdate(BaseModel):
    status: ContactRequestStatus


class ContactRequestRead(TimestampedRead):
    id: int
    name: str
    email: EmailStr
    message: str
    locale: str
    source_page: str | None = None
    status: ContactRequestStatus

