from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleDirectionMatch(Base, TimestampedMixin):
    __tablename__ = "style_direction_matches"
    __table_args__ = (
        Index("ix_style_direction_matches_status", "match_status"),
        Index("ix_style_direction_matches_discovered_slug", "discovered_slug"),
        Index("ix_style_direction_matches_style_direction_id", "style_direction_id"),
        UniqueConstraint("source_name", "source_url", name="uq_style_direction_match_source_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    style_direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_directions.id", ondelete="SET NULL"),
        nullable=True,
    )
    match_status: Mapped[str] = mapped_column(String(32), nullable=False)
    match_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_snapshot_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
