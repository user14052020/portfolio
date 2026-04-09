from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class Style(Base, TimestampedMixin):
    __tablename__ = "styles"
    __table_args__ = (
        Index("ix_styles_status", "status"),
        Index("ix_styles_source_primary_id", "source_primary_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    source_primary_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    short_definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    first_ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
