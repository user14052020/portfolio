from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourceLink(Base, TimestampedMixin):
    __tablename__ = "style_source_links"
    __table_args__ = (
        Index("ix_style_source_links_page_type", "source_page_id", "link_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("style_sources.id", ondelete="CASCADE"), nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    link_type: Mapped[str] = mapped_column(Text, nullable=False)
