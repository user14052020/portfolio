from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourcePage(Base, TimestampedMixin):
    __tablename__ = "style_source_pages"
    __table_args__ = (
        Index("ix_style_source_pages_source_url", "source_name", "page_url", unique=True),
        Index("ix_style_source_pages_source_kind", "source_name", "page_kind"),
        Index("ix_style_source_pages_source_remote_page", "source_name", "remote_page_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    page_kind: Mapped[str] = mapped_column(String(32), default="style", nullable=False)
    remote_page_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latest_content_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
