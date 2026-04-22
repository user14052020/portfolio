from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class StylistChatSession(Base, TimestampedMixin):
    __tablename__ = "stylist_chat_sessions"
    __table_args__ = (
        Index("ix_stylist_chat_sessions_last_message_at", "last_message_at"),
        Index("ix_stylist_chat_sessions_client_ip", "client_ip"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locale: Mapped[str | None] = mapped_column(String(5), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_active_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_decision_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
