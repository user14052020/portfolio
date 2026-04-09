from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleSourceFetchLog(Base):
    __tablename__ = "style_source_fetch_logs"
    __table_args__ = (
        Index("ix_style_source_fetch_logs_source_name_fetched_at", "source_name", "fetched_at"),
        Index("ix_style_source_fetch_logs_fetch_mode", "fetch_mode"),
        Index("ix_style_source_fetch_logs_request_url", "request_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    fetch_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    request_method: Mapped[str] = mapped_column(String(16), nullable=False)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
