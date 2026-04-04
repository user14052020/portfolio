from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mixins import Base, TimestampedMixin


class SiteSettings(Base, TimestampedMixin):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(String(255), default="Vadim Portfolio")
    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assistant_name_ru: Mapped[str] = mapped_column(String(255), default="Валентин")
    assistant_name_en: Mapped[str] = mapped_column(String(255), default="Jose")
    hero_title_ru: Mapped[str] = mapped_column(String(255))
    hero_title_en: Mapped[str] = mapped_column(String(255))
    hero_subtitle_ru: Mapped[str] = mapped_column(Text)
    hero_subtitle_en: Mapped[str] = mapped_column(Text)
    about_title_ru: Mapped[str] = mapped_column(String(255))
    about_title_en: Mapped[str] = mapped_column(String(255))
    about_text_ru: Mapped[str] = mapped_column(Text)
    about_text_en: Mapped[str] = mapped_column(Text)
    socials: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
