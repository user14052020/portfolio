from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleRelationFacet(Base):
    __tablename__ = "style_relation_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_relation_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    related_styles_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    overlap_styles_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preceded_by_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    succeeded_by_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    brands_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    platforms_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    origin_regions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    era_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
