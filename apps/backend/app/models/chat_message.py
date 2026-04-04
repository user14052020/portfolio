from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import ChatMessageRole, sql_enum
from app.models.mixins import Base, TimestampedMixin


class ChatMessage(Base, TimestampedMixin):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_session_created", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(120), index=True)
    role: Mapped[ChatMessageRole] = mapped_column(sql_enum(ChatMessageRole, name="chat_message_role"))
    locale: Mapped[str] = mapped_column(String(5), default="en")
    content: Mapped[str] = mapped_column(Text)
    generation_job_id: Mapped[int | None] = mapped_column(ForeignKey("generation_jobs.id"), nullable=True)
    uploaded_asset_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_assets.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    generation_job = relationship("GenerationJob", back_populates="messages")
    uploaded_asset = relationship("UploadedAsset")
