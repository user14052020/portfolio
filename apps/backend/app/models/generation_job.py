from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import GenerationProvider, GenerationStatus, sql_enum
from app.models.mixins import Base, TimestampedMixin


class GenerationJob(Base, TimestampedMixin):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index("ix_generation_jobs_status_created_at", "status", "created_at"),
        Index("ix_generation_jobs_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[GenerationProvider] = mapped_column(
        sql_enum(GenerationProvider, name="generation_provider"), default=GenerationProvider.COMFYUI
    )
    status: Mapped[GenerationStatus] = mapped_column(
        sql_enum(GenerationStatus, name="generation_status"), default=GenerationStatus.PENDING, nullable=False
    )
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    recommendation_ru: Mapped[str] = mapped_column(Text)
    recommendation_en: Mapped[str] = mapped_column(Text)
    input_asset_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_assets.id"), nullable=True, index=True)
    result_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_job_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    body_height_cm: Mapped[int | None] = mapped_column(nullable=True)
    body_weight_kg: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    input_asset = relationship("UploadedAsset")
    messages = relationship("ChatMessage", back_populates="generation_job")
