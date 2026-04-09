from sqlalchemy import ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleProfile(Base, TimestampedMixin):
    __tablename__ = "style_profiles"
    __table_args__ = (
        UniqueConstraint("style_id", name="uq_style_profiles_style_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    essence: Mapped[str | None] = mapped_column(Text, nullable=True)
    fashion_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    cultural_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood_keywords_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    color_palette_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    materials_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    silhouettes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    garments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    footwear_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    accessories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    hair_makeup_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    patterns_textures_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    seasonality_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    occasion_fit_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    negative_constraints_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    styling_advice_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    image_prompt_notes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
