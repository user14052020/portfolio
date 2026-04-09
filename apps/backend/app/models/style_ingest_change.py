from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StyleIngestChange(Base, TimestampedMixin):
    __tablename__ = "style_ingest_changes"
    __table_args__ = (
        Index("ix_style_ingest_changes_run_id", "run_id"),
        Index("ix_style_ingest_changes_style_id", "style_id"),
        Index("ix_style_ingest_changes_change_type", "change_type"),
        Index("ix_style_ingest_changes_field_name", "field_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("style_ingest_runs.id", ondelete="CASCADE"), nullable=False)
    style_id: Mapped[int | None] = mapped_column(ForeignKey("styles.id", ondelete="SET NULL"), nullable=True)
    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_value_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
