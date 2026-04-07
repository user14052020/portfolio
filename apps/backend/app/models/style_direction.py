from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleDirection(Base, TimestampedMixin):
    __tablename__ = "style_directions"
    __table_args__ = (
        Index("ix_style_directions_active_sort", "is_active", "sort_order"),
        Index("ix_style_directions_source_group", "source_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    source_title: Mapped[str] = mapped_column(Text)
    source_group: Mapped[str] = mapped_column(String(32), default="styles-1", nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    descriptor_en: Mapped[str] = mapped_column(String(255), nullable=False)
    selection_weight: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
