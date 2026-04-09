from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleTaxonomyNode(Base, TimestampedMixin):
    __tablename__ = "style_taxonomy_nodes"
    __table_args__ = (
        Index("ix_style_taxonomy_nodes_type_slug", "taxonomy_type", "slug"),
        UniqueConstraint("taxonomy_type", "slug", name="uq_style_taxonomy_type_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    taxonomy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
