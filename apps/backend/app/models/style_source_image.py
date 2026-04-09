from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourceImage(Base, TimestampedMixin):
    __tablename__ = "style_source_images"
    __table_args__ = (
        Index("ix_style_source_images_page_position", "source_page_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("style_sources.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    license_if_available: Mapped[str | None] = mapped_column(Text, nullable=True)
