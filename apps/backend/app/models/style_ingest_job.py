from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleIngestJob(Base, TimestampedMixin):
    __tablename__ = "style_ingest_jobs"
    __table_args__ = (
        Index("ix_style_ingest_jobs_dedupe_key", "dedupe_key", unique=True),
        Index("ix_style_ingest_jobs_status_available", "status", "available_at"),
        Index("ix_style_ingest_jobs_source_type_status", "source_name", "job_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_page_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_page_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
