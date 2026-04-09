from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleRelation(Base, TimestampedMixin):
    __tablename__ = "style_relations"
    __table_args__ = (
        Index("ix_style_relations_source_style_id", "source_style_id"),
        Index("ix_style_relations_target_style_id", "target_style_id"),
        Index("ix_style_relations_relation_type", "relation_type"),
        Index("ix_style_relations_source_evidence_id", "source_evidence_id"),
        UniqueConstraint(
            "source_style_id",
            "target_style_id",
            "relation_type",
            name="uq_style_relation_triplet",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    target_style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_evidences.id", ondelete="SET NULL"),
        nullable=True,
    )
