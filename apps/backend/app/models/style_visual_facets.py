from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleVisualFacet(Base):
    __tablename__ = "style_visual_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_visual_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    palette_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    lighting_mood_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    photo_treatment_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    visual_motifs_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    patterns_textures_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    platform_visual_cues_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
