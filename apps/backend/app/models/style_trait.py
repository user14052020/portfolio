from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleTrait(Base, TimestampedMixin):
    __tablename__ = "style_traits"
    __table_args__ = (
        Index("ix_style_traits_style_trait", "style_id", "trait_type"),
        Index("ix_style_traits_trait_value", "trait_value"),
        Index("ix_style_traits_source_evidence_id", "source_evidence_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    trait_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trait_value: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_evidences.id", ondelete="SET NULL"),
        nullable=True,
    )
