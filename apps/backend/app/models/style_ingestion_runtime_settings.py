from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleIngestionRuntimeSettings(Base, TimestampedMixin):
    __tablename__ = "style_ingestion_runtime_settings"
    __table_args__ = (UniqueConstraint("source_name", name="uq_style_ingestion_runtime_settings_source_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    min_delay_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    max_delay_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    jitter_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    empty_body_cooldown_min_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    empty_body_cooldown_max_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    retry_backoff_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    retry_backoff_jitter_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    worker_idle_sleep_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    worker_lease_ttl_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    worker_lease_heartbeat_interval_seconds: Mapped[float] = mapped_column(Float, nullable=False)
