from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourceSection(Base, TimestampedMixin):
    __tablename__ = "style_source_sections"
    __table_args__ = (
        Index("ix_style_source_sections_source_page_order", "source_page_id", "section_order"),
        Index("ix_style_source_sections_section_hash", "section_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("style_sources.id", ondelete="CASCADE"), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_hash: Mapped[str] = mapped_column(Text, nullable=False)
