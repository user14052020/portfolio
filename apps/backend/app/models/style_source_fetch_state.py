from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourceFetchState(Base, TimestampedMixin):
    __tablename__ = "style_source_fetch_states"
    __table_args__ = (
        Index("ix_style_source_fetch_states_source_name", "source_name", unique=True),
        Index("ix_style_source_fetch_states_mode", "mode"),
        Index("ix_style_source_fetch_states_next_allowed_at", "next_allowed_at"),
        Index("ix_style_source_fetch_states_worker_lease_expires_at", "worker_lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_empty_body_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_empty_bodies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_min_interval_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    worker_lease_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_lease_acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_lease_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
