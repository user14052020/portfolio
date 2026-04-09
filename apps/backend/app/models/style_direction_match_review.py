from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleDirectionMatchReview(Base, TimestampedMixin):
    __tablename__ = "style_direction_match_reviews"
    __table_args__ = (
        Index("ix_style_direction_match_reviews_review_status", "review_status"),
        Index("ix_style_direction_match_reviews_selected_style_direction_id", "selected_style_direction_id"),
        UniqueConstraint("match_id", name="uq_style_direction_match_reviews_match_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("style_direction_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    resolution_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    selected_style_direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_directions.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
