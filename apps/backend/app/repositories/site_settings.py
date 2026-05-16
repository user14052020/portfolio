from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.stylist_runtime_settings import (
    DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
    DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
    DEFAULT_MESSAGE_COOLDOWN_SECONDS,
    DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
)
from app.models import SiteSettings
from app.repositories.base import BaseRepository


def build_default_site_settings_payload() -> dict[str, Any]:
    return {
        "brand_name": "Вадим Махаррам",
        "contact_email": "hello@vadim.dev",
        "contact_phone": None,
        "assistant_name_ru": "Валентин",
        "assistant_name_en": "Jose",
        "hero_title_ru": "Разрабатываю веб-продукты с 3D-графикой и motion-интерфейсами",
        "hero_title_en": "I build web products with 3D graphics and motion interfaces",
        "hero_subtitle_ru": "Создаю быстрые, интерактивные и визуально продуманные решения для бизнеса и стартапов.",
        "hero_subtitle_en": "I create fast, interactive and visually considered solutions for businesses and startups.",
        "about_title_ru": "Обо мне",
        "about_title_en": "About me",
        "about_text_ru": "Full-stack architect с сильным уклоном в creative tech, генеративный AI и визуальные интерфейсы.",
        "about_text_en": "Full-stack architect focused on creative tech, generative AI and visual interfaces.",
        "socials": {
            "telegram": "https://t.me/example",
            "github": "https://github.com/example",
        },
        "skills": ["TypeScript", "Next.js", "Three.js", "GSAP", "Framer Motion"],
        "homepage_content": {
            "brand_name_ru": "Вадим Махаррам",
            "brand_name_en": "Vadim Makharram",
            "hero_eyebrow_items": ["FRONTEND", "3D", "MOTION"],
            "technologies_label_ru": "Технологии",
            "technologies_label_en": "Technologies",
            "project_stack_label_ru": "Стек",
            "project_stack_label_en": "Stack",
            "hero_preview": {
                "visual_variant": "dashboard-dark",
                "video_duration": "0:45",
            },
            "header_cta_label_ru": "Связаться со мной",
            "header_cta_label_en": "Contact me",
            "contact_title_ru": "Есть проект?\nДавайте обсудим",
            "contact_title_en": "Have a project?\nLet's discuss",
            "contact_description_ru": "Опишите задачу - предложу решение\nи подскажу оптимальный подход.",
            "contact_description_en": "Describe the task - I will suggest a solution\nand the right implementation path.",
            "telegram_label_ru": "Telegram",
            "telegram_label_en": "Telegram",
            "email_label_ru": "Email",
            "email_label_en": "Email",
            "chat_section_title_ru": "AI-стилист",
            "chat_section_title_en": "AI stylist",
            "chat_section_description_ru": "Чат-бот временно вынесен в конец страницы.",
            "chat_section_description_en": "The chatbot block is temporarily placed at the end of the page.",
        },
        "chat_bot_enabled": False,
        "daily_generation_limit_non_admin": DEFAULT_DAILY_GENERATION_LIMIT_NON_ADMIN,
        "daily_chat_seconds_limit_non_admin": DEFAULT_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
        "message_cooldown_seconds": DEFAULT_MESSAGE_COOLDOWN_SECONDS,
        "try_other_style_cooldown_seconds": DEFAULT_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
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
