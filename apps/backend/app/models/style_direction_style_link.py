from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleDirectionStyleLink(Base, TimestampedMixin):
    __tablename__ = "style_direction_style_links"
    __table_args__ = (
        Index("ix_style_direction_style_links_style_id", "style_id"),
        Index("ix_style_direction_style_links_link_status", "link_status"),
        UniqueConstraint("style_direction_id", name="uq_style_direction_style_links_style_direction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_direction_id: Mapped[int] = mapped_column(
        ForeignKey("style_directions.id", ondelete="CASCADE"),
        nullable=False,
    )
    style_id: Mapped[int] = mapped_column(
        ForeignKey("styles.id", ondelete="CASCADE"),
        nullable=False,
    )
    linked_via_match_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_direction_matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    link_status: Mapped[str] = mapped_column(String(32), nullable=False)
    link_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    link_note: Mapped[str | None] = mapped_column(Text, nullable=True)
