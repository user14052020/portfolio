from sqlalchemy import Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleTaxonomyLink(Base, TimestampedMixin):
    __tablename__ = "style_taxonomy_links"
    __table_args__ = (
        Index("ix_style_taxonomy_links_style_id", "style_id"),
        Index("ix_style_taxonomy_links_taxonomy_node_id", "taxonomy_node_id"),
        Index("ix_style_taxonomy_links_source_evidence_id", "source_evidence_id"),
        UniqueConstraint("style_id", "taxonomy_node_id", name="uq_style_taxonomy_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    taxonomy_node_id: Mapped[int] = mapped_column(
        ForeignKey("style_taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    link_strength: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_source_evidences.id", ondelete="SET NULL"),
        nullable=True,
    )
