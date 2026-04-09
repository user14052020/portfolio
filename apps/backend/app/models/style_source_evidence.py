from sqlalchemy import Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleSourceEvidence(Base, TimestampedMixin):
    __tablename__ = "style_source_evidences"
    __table_args__ = (
        Index("ix_style_source_evidences_page_kind", "source_page_id", "evidence_kind"),
        Index("ix_style_source_evidences_section_id", "source_section_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_page_id: Mapped[int] = mapped_column(ForeignKey("style_sources.id", ondelete="CASCADE"), nullable=False)
    source_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
