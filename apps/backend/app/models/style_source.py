from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSource(Base, TimestampedMixin):
    __tablename__ = "style_sources"
    __table_args__ = (
        Index("ix_style_sources_site_url", "source_site", "source_url"),
        Index("ix_style_sources_source_hash", "source_hash"),
        Index("ix_style_sources_last_seen_at", "last_seen_at"),
        Index("ix_style_sources_site_page_id", "source_site", "remote_page_id"),
        Index("ix_style_sources_site_revision_id", "source_site", "remote_revision_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_site: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    fetch_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remote_page_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remote_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html: Mapped[str] = mapped_column(Text, nullable=False)
    raw_wikitext: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_sections_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    raw_links_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    normalizer_version: Mapped[str] = mapped_column(Text, nullable=False)
