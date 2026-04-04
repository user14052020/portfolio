from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class PageScene(Base, TimestampedMixin):
    __tablename__ = "page_scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    scene_key: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

