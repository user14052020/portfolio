from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StylistStyleExposure(Base, TimestampedMixin):
    __tablename__ = "stylist_style_exposures"
    __table_args__ = (
        UniqueConstraint("session_id", "style_direction_id", "shown_on", name="uq_style_exposure_session_style_day"),
        Index("ix_style_exposures_session_day", "session_id", "shown_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(120), index=True)
    style_direction_id: Mapped[int] = mapped_column(ForeignKey("style_directions.id"), nullable=False, index=True)
    shown_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
