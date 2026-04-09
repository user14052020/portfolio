from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSource(Base, TimestampedMixin):
    __tablename__ = "style_sources"
    __table_args__ = (
        Index("ix_style_sources_site_url", "source_site", "source_url"),
        Index("ix_style_sources_source_hash", "source_hash"),
        Index("ix_style_sources_last_seen_at", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_site: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    raw_html: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_sections_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    normalizer_version: Mapped[str] = mapped_column(Text, nullable=False)
