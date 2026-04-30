from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.stylist_runtime_settings import (
    DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
    DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
    DEFAULT_MESSAGE_COOLDOWN_SECONDS,
    DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
)
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
    daily_generation_limit_non_admin: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
        nullable=False,
    )
    daily_chat_seconds_limit_non_admin: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
        nullable=False,
    )
    message_cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_MESSAGE_COOLDOWN_SECONDS,
        nullable=False,
    )
    try_other_style_cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
        nullable=False,
    )
    knowledge_runtime_flags_json: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    knowledge_provider_priorities_json: Mapped[dict[str, int]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    voice_runtime_flags_json: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
