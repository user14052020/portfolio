from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums import ContactRequestStatus, sql_enum
from app.models.mixins import Base, TimestampedMixin


class ContactRequest(Base, TimestampedMixin):
    __tablename__ = "contact_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    message: Mapped[str] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(5), default="en")
    source_page: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[ContactRequestStatus] = mapped_column(
        sql_enum(ContactRequestStatus, name="contact_request_status"),
        default=ContactRequestStatus.NEW,
        nullable=False,
    )
