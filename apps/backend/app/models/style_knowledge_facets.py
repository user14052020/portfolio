from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base


class StyleKnowledgeFacet(Base):
    __tablename__ = "style_knowledge_facets"
    __table_args__ = (
        UniqueConstraint("style_id", "facet_version", name="uq_style_knowledge_facets_style_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    facet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    core_definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_style_logic_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    styling_rules_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    casual_adaptations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    statement_pieces_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status_markers_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    overlap_context_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    historical_notes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    negative_guidance_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
