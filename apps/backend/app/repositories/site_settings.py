from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.stylist_runtime_settings import (
    DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
    DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
    DEFAULT_MESSAGE_COOLDOWN_SECONDS,
    DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
)
from app.domain.knowledge_runtime_settings import DEFAULT_KNOWLEDGE_PROVIDER_PRIORITIES
from app.models import SiteSettings
from app.repositories.base import BaseRepository


def build_default_site_settings_payload() -> dict[str, Any]:
    return {
        "brand_name": "Vadim Portfolio",
        "contact_email": "hello@vadim.dev",
        "contact_phone": None,
        "assistant_name_ru": "Валентин",
        "assistant_name_en": "Jose",
        "hero_title_ru": "Креативный full-stack developer",
        "hero_title_en": "Creative full-stack developer",
        "hero_subtitle_ru": "Создаю продуктовые интерфейсы, AI-инструменты и motion-driven digital experiences.",
        "hero_subtitle_en": "I build product interfaces, AI tools and motion-driven digital experiences.",
        "about_title_ru": "Обо мне",
        "about_title_en": "About me",
        "about_text_ru": "Full-stack architect с сильным уклоном в creative tech, генеративный AI и визуальные интерфейсы.",
        "about_text_en": "Full-stack architect focused on creative tech, generative AI and visual interfaces.",
        "socials": {
            "telegram": "https://t.me/example",
            "github": "https://github.com/example",
        },
        "skills": ["FastAPI", "Next.js", "ComfyUI", "Motion Design", "Three.js"],
        "daily_generation_limit_non_admin": DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
        "daily_chat_seconds_limit_non_admin": DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
        "message_cooldown_seconds": DEFAULT_MESSAGE_COOLDOWN_SECONDS,
        "try_other_style_cooldown_seconds": DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
        "knowledge_runtime_flags_json": {},
        "knowledge_provider_priorities_json": dict(DEFAULT_KNOWLEDGE_PROVIDER_PRIORITIES),
        "voice_runtime_flags_json": {},
    }


class SiteSettingsRepository(BaseRepository[SiteSettings]):
    def __init__(self) -> None:
        super().__init__(SiteSettings)

    async def get_singleton(self, session: AsyncSession) -> SiteSettings | None:
        result = await session.execute(select(SiteSettings).limit(1))
        return result.scalar_one_or_none()

    async def get_or_create_singleton(self, session: AsyncSession) -> SiteSettings:
        settings = await self.get_singleton(session)
        if settings is not None:
            return settings
        return await self.create(session, build_default_site_settings_payload())


site_settings_repository = SiteSettingsRepository()
