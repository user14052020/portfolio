from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleImageFacet(Base):
    __tablename__ = "style_image_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_image_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    hero_garments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    secondary_garments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    core_accessories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    props_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    materials_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    composition_cues_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    negative_constraints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    visual_motifs_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    lighting_mood_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    photo_treatment_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
