from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleIngestRun(Base, TimestampedMixin):
    __tablename__ = "style_ingest_runs"
    __table_args__ = (
        Index("ix_style_ingest_runs_started_at", "started_at"),
        Index("ix_style_ingest_runs_source_name", "source_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    checkpoint_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    styles_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    styles_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    styles_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    styles_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    styles_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalizer_version: Mapped[str | None] = mapped_column(Text, nullable=True)
