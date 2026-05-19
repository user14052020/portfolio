"""Application bootstrap seed.

This script creates only baseline application data such as roles, admin user,
site settings, demo projects, demo blog content and scenes.

It does not populate the style catalog, does not import legacy TXT style lists
and does not run parser ingestion. Style knowledge is loaded only through the
API/job-driven style ingestion pipeline.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.integrations.elasticsearch import close_elasticsearch_client
from app.models import BlogCategory, BlogPost, PageScene, Project, Role, SiteSettings, User
from app.models.enums import BlogPostType, RoleCode
from app.seed_data.showcase_projects import DEFAULT_SHOWCASE_PROJECTS
from app.services.search import search_service
from app.utils.slug import build_slug


settings = get_settings()


async def seed_roles(session) -> dict[str, Role]:
    existing = (await session.execute(select(Role))).scalars().all()
    roles = {role.name: role for role in existing}
    if RoleCode.ADMIN.value not in roles:
        session.add(Role(name=RoleCode.ADMIN.value, description="Platform administrator"))
    if RoleCode.EDITOR.value not in roles:
        session.add(Role(name=RoleCode.EDITOR.value, description="Content editor"))
    await session.flush()
    existing = (await session.execute(select(Role))).scalars().all()
    return {role.name: role for role in existing}


async def seed_admin(session, roles: dict[str, Role]) -> None:
    existing_admin = await session.scalar(select(User).where(User.email == settings.initial_admin_email))
    if existing_admin:
        return
    session.add(
        User(
            email=settings.initial_admin_email,
            full_name="Portfolio Admin",
            hashed_password=get_password_hash(settings.initial_admin_password),
            is_active=True,
            role_id=roles[RoleCode.ADMIN.value].id,
        )
    )


async def seed_site_settings(session) -> None:
    if await session.scalar(select(SiteSettings.id)):
        return
    session.add(
        SiteSettings(
            brand_name="Вадим Махаррам",
            contact_email="hello@vadim.dev",
            contact_phone="+7 (900) 000-00-00",
            assistant_name_ru="Валентин",
            assistant_name_en="Jose",
            hero_title_ru="Разрабатываю веб-продукты с 3D-графикой и motion-интерфейсами",
            hero_title_en="I build web products with 3D graphics and motion interfaces",
            hero_subtitle_ru="Создаю быстрые, интерактивные и визуально продуманные решения для бизнеса и стартапов.",
            hero_subtitle_en="I create fast, interactive and visually considered solutions for businesses and startups.",
            about_title_ru="Обо мне",
            about_title_en="About me",
            about_text_ru="Senior full-stack architect и lead developer. Работаю с FastAPI, Next.js, real-time UI, creative coding и AI-пайплайнами.",
            about_text_en="Senior full-stack architect and lead developer. I work with FastAPI, Next.js, real-time UI, creative coding and AI pipelines.",
            socials={
                "telegram": "https://t.me/example",
                "vk": "",
                "youtube": "",
                "rutube": "",
                "dzen": "",
                "github": "https://github.com/example",
                "linkedin": "https://linkedin.com/in/example",
            },
            skills=["TypeScript", "Next.js", "Three.js", "GSAP", "Framer Motion"],
            homepage_content={
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
            chat_bot_enabled=False,
        )
    )


async def seed_projects(session) -> list[Project]:
    existing = (await session.execute(select(Project))).scalars().all()
    if existing:
        return existing

    projects = [Project(**project_payload) for project_payload in DEFAULT_SHOWCASE_PROJECTS]
    session.add_all(projects)
    await session.flush()
    return projects


async def seed_blog(session) -> list[BlogPost]:
    existing = (await session.execute(select(BlogPost))).scalars().all()
    if existing:
        return existing

    categories = [
        BlogCategory(slug="engineering", name_ru="Разработка", name_en="Engineering"),
        BlogCategory(slug="motion", name_ru="Моушн", name_en="Motion"),
    ]
    session.add_all(categories)
    await session.flush()
    categories_map = {item.slug: item for item in categories}

    posts = [
        BlogPost(
            slug=build_slug("Designing AI-first Portfolio Systems"),
            title_ru="Как проектировать AI-first portfolio системы",
            title_en="Designing AI-first Portfolio Systems",
            excerpt_ru="Подход к совмещению персонального бренда, AI-функций и редактируемого контента в одном продукте.",
            excerpt_en="How to combine personal branding, AI features and editable content in a single product.",
            content_ru=(
                "## Архитектура\n\n"
                "Портфолио перестает быть только витриной и становится инструментом взаимодействия.\n\n"
                "### Что важно\n\n"
                "- единый контур данных для проектов, блога и AI-функций\n"
                "- мультиязычный контент\n"
                "- управляемая интеграция с генераторами"
            ),
            content_en=(
                "## Architecture\n\n"
                "A portfolio stops being a static showcase and becomes an interaction product.\n\n"
                "### Key principles\n\n"
                "- one data model for portfolio, blog and AI features\n"
                "- multilingual content\n"
                "- controlled generator integrations"
            ),
            cover_image="https://placehold.co/1600x960/efe4d5/111827?text=AI-first+Portfolio",
            video_url=None,
            post_type=BlogPostType.ARTICLE,
            tags=["ai", "architecture", "portfolio"],
            seo_title_ru="AI-first Portfolio Systems",
            seo_title_en="Designing AI-first Portfolio Systems",
            seo_description_ru="Архитектурный взгляд на современные portfolio-системы.",
            seo_description_en="Architectural notes on modern portfolio systems.",
            page_scene_key="blog-particle-field",
            is_published=True,
            published_at=datetime.now(UTC),
            category_id=categories_map["engineering"].id,
        ),
        BlogPost(
            slug=build_slug("Motion Direction Notes"),
            title_ru="Motion Direction Notes",
            title_en="Motion Direction Notes",
            excerpt_ru="Короткий видеоблог о темпе, паузах и визуальном дыхании интерфейсов.",
            excerpt_en="A short video blog on rhythm, pauses and visual breathing in interfaces.",
            content_ru="Видео-заметки о том, как motion влияет на ощущение дорогого продукта.",
            content_en="Video notes on how motion shapes the perception of a premium product.",
            cover_image="https://placehold.co/1600x960/e4d9c7/111827?text=Motion+Direction",
            video_url="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
            post_type=BlogPostType.VIDEO,
            tags=["motion", "video", "design"],
            seo_title_ru="Motion Direction Notes",
            seo_title_en="Motion Direction Notes",
            seo_description_ru="Видеозаметки про motion-дизайн и визуальный ритм.",
            seo_description_en="Video notes on motion design and interface rhythm.",
            page_scene_key="blog-wave-grid",
            is_published=True,
            published_at=datetime.now(UTC),
            category_id=categories_map["motion"].id,
        ),
    ]
    session.add_all(posts)
    return posts


async def seed_scenes(session) -> None:
    existing = (await session.execute(select(PageScene))).scalars().all()
    if existing:
        return
    session.add_all(
        [
            PageScene(page_key="home", scene_key="home-sculpture", title="Home Sculpture", subtitle="Hero ambient orb", config={"accent": "#d0a46d"}),
            PageScene(page_key="project", scene_key="project-hero-orb", title="Project Orb", subtitle="Project hero 3D placeholder", config={"accent": "#9fb7a5"}),
            PageScene(page_key="blog", scene_key="blog-particle-field", title="Blog Particles", subtitle="Blog page ambient particles", config={"accent": "#b36f4e"}),
            PageScene(page_key="admin", scene_key="admin-grid", title="Admin Grid", subtitle="Structured dashboard grid scene", config={"accent": "#64748b"}),
        ]
    )


async def main() -> None:
    try:
        async with SessionLocal() as session:
            roles = await seed_roles(session)
            await seed_admin(session, roles)
            await seed_site_settings(session)
            projects = await seed_projects(session)
            posts = await seed_blog(session)
            await seed_scenes(session)
            await session.commit()

            await search_service.ensure_indices()
            for project in projects:
                await search_service.index_project(project)
            for post in posts:
                await search_service.index_blog_post(post)
    finally:
        await close_elasticsearch_client()


if __name__ == "__main__":
    asyncio.run(main())
