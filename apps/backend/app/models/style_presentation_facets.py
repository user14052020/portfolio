from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StylePresentationFacet(Base):
    __tablename__ = "style_presentation_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_presentation_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    short_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    one_sentence_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_makes_it_distinct_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
