from sqlalchemy import Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StylistSessionState(Base, TimestampedMixin):
    __tablename__ = "stylist_session_states"
    __table_args__ = (
        Index("ix_stylist_session_states_active_intent", "active_intent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    active_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
