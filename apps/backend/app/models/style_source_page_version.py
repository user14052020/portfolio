from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleSourcePageVersion(Base):
    __tablename__ = "style_source_page_versions"
    __table_args__ = (
        Index("ix_style_source_page_versions_page_revision", "source_page_id", "remote_revision_id"),
        Index("ix_style_source_page_versions_page_fingerprint", "source_page_id", "content_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("style_source_pages.id", ondelete="CASCADE"), nullable=False)
    fetch_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    remote_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_html: Mapped[str] = mapped_column(Text, nullable=False)
    raw_wikitext: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_sections_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    raw_links_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
