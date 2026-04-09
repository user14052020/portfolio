from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleAlias(Base, TimestampedMixin):
    __tablename__ = "style_aliases"
    __table_args__ = (
        Index("ix_style_aliases_alias_language", "alias", "language"),
        Index("ix_style_aliases_style_id", "style_id"),
        UniqueConstraint("style_id", "alias", "language", name="uq_style_alias_style_language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_primary_match_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
