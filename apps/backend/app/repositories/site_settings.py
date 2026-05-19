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
            "vk": "",
            "youtube": "",
            "rutube": "",
            "dzen": "",
            "github": "https://github.com/example",
        },
        "skills": ["TypeScript", "Next.js", "Three.js", "GSAP", "Framer Motion"],
        "homepage_content": {
            "brand_name_ru": "Вадим Махаррам",
            "brand_name_en": "Vadim Makharram",
            "hero_eyebrow_items": ["FRONTEND", "3D", "MOTION"],
            "hero_eyebrow_items_ru": ["ФРОНТЕНД", "3D", "МОУШЕН"],
            "hero_eyebrow_items_en": ["FRONTEND", "3D", "MOTION"],
            "hero_title_rotating_items_ru": [
                "сайты",
                "мобильные приложения",
                "десктопные приложения",
                "3D-анимацию",
                "графический дизайн для видео",
            ],
            "hero_title_rotating_items_en": [
                "websites",
                "mobile apps",
                "desktop apps",
                "3D animation",
                "video graphic design",
            ],
            "hero_title_rotating_interval_ms": 1800,
            "hero_title_rotating_animation_ms": 900,
            "hero_title_rotating_accent_color": "#4f63f6",
            "technologies_label_ru": "Технологии",
            "technologies_label_en": "Technologies",
            "project_stack_label_ru": "Стек",
            "project_stack_label_en": "Stack",
            "project_demo_cta_label_ru": "Нажмите, чтобы увидеть демо",
            "project_demo_cta_label_en": "Click to view demo",
            "hero_preview": {
                "visual_variant": "dashboard-dark",
                "video_duration": "0:45",
                "video_url": None,
                "cover_image": None,
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
            "site_meta": {
                "title_ru": "Вадим Махаррам - веб-продукты с 3D и motion",
                "title_en": "Vadim Makharram - web products with 3D and motion",
                "description_ru": "Разрабатываю быстрые веб-продукты с 3D-графикой, motion-интерфейсами и продуманной архитектурой.",
                "description_en": "I build fast web products with 3D graphics, motion interfaces and thoughtful architecture.",
                "keywords": ["frontend", "3d", "motion", "next.js", "three.js", "portfolio"],
                "canonical_url": "https://maharram.ru",
                "og_title_ru": "Вадим Махаррам",
                "og_title_en": "Vadim Makharram",
                "og_description_ru": "Веб-продукты с 3D-графикой и motion-интерфейсами.",
                "og_description_en": "Web products with 3D graphics and motion interfaces.",
                "og_image": None,
                "twitter_card": "summary_large_image",
                "theme_color": "#f7f7f5",
                "robots_index": True,
                "robots_follow": True,
            },
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
