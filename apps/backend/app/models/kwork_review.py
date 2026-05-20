from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class KworkReview(Base, TimestampedMixin):
    __tablename__ = "kwork_reviews"
    __table_args__ = (
        Index("ix_kwork_reviews_published_sort", "is_published", "sort_order"),
        Index("ix_kwork_reviews_external_id", "external_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_platform: Mapped[str] = mapped_column(String(64), default="kwork", nullable=False)
    review_type: Mapped[str] = mapped_column(String(32), default="positive", nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    project_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_ago: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
