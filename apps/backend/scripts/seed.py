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
from app.models import BlogCategory, BlogPost, PageScene, Project, ProjectMedia, Role, SiteSettings, User
from app.models.enums import BlogPostType, MediaType, RoleCode
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
            brand_name="Vadim Creative Portfolio",
            contact_email="hello@vadim.dev",
            contact_phone="+7 (900) 000-00-00",
            assistant_name_ru="Валентин",
            assistant_name_en="Jose",
            hero_title_ru="AI, full-stack и визуальные системы",
            hero_title_en="AI, full-stack and visual systems",
            hero_subtitle_ru="Проектирую и собираю digital-продукты на стыке backend, frontend, motion и генеративного AI.",
            hero_subtitle_en="I architect and build digital products across backend, frontend, motion and generative AI.",
            about_title_ru="Обо мне",
            about_title_en="About me",
            about_text_ru="Senior full-stack architect и lead developer. Работаю с FastAPI, Next.js, real-time UI, creative coding и AI-пайплайнами.",
            about_text_en="Senior full-stack architect and lead developer. I work with FastAPI, Next.js, real-time UI, creative coding and AI pipelines.",
            socials={
                "telegram": "https://t.me/example",
                "github": "https://github.com/example",
                "linkedin": "https://linkedin.com/in/example",
            },
            skills=["FastAPI", "Next.js", "Mantine", "Tailwind", "ComfyUI", "React Three Fiber"],
        )
    )


async def seed_projects(session) -> list[Project]:
    existing = (await session.execute(select(Project))).scalars().all()
    if existing:
        return existing

    projects = [
        Project(
            slug=build_slug("AI Stylist Studio"),
            title_ru="AI Stylist Studio",
            title_en="AI Stylist Studio",
            summary_ru="Платформа персонального стилиста с генерацией fashion flat-lay через локальный ComfyUI.",
            summary_en="Personal stylist platform with fashion flat-lay generation via local-network ComfyUI.",
            description_ru="Full-stack продукт с chat UX, upload пайплайном, генерацией образов и админкой для управления контентом и задачами.",
            description_en="A full-stack product with chat UX, upload pipeline, outfit generation and an admin panel for content and jobs management.",
            stack=["FastAPI", "Next.js", "PostgreSQL", "Redis", "ComfyUI", "Mantine"],
            cover_image="https://placehold.co/1600x960/e8ddd2/111827?text=AI+Stylist+Studio",
            preview_video_url="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
            repository_url="https://github.com/example/ai-stylist-studio",
            live_url="https://example.com/ai-stylist",
            page_scene_key="project-hero-orb",
            seo_title_ru="AI Stylist Studio",
            seo_title_en="AI Stylist Studio",
            seo_description_ru="AI-стилист с генерацией образов и creative portfolio UI.",
            seo_description_en="AI stylist with outfit generation and creative portfolio UI.",
            sort_order=1,
            is_featured=True,
            is_published=True,
        ),
        Project(
            slug=build_slug("Creative Motion Dashboard"),
            title_ru="Creative Motion Dashboard",
            title_en="Creative Motion Dashboard",
            summary_ru="Платформа для презентации motion-дизайна и 3D-контента в виде creative studio dashboard.",
            summary_en="Platform for showcasing motion design and 3D content inside a creative studio dashboard.",
            description_ru="Собственный дизайн-системный слой, видеопревью, мультиязычный CMS-контур и 3D placeholder сцены на странице проекта.",
            description_en="Custom design-system layer, video previews, multilingual CMS flow and 3D placeholder scenes on project pages.",
            stack=["Next.js", "TypeScript", "Mantine", "Tailwind", "React Three Fiber"],
            cover_image="https://placehold.co/1600x960/f3efe6/111827?text=Creative+Motion+Dashboard",
            preview_video_url="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
            repository_url="https://github.com/example/creative-motion-dashboard",
            live_url="https://example.com/motion-dashboard",
            page_scene_key="project-motion-ribbon",
            seo_title_ru="Creative Motion Dashboard",
            seo_title_en="Creative Motion Dashboard",
            seo_description_ru="Motion и portfolio UX в стилистике studio dashboard.",
            seo_description_en="Motion and portfolio UX in a creative studio dashboard language.",
            sort_order=2,
            is_featured=True,
            is_published=True,
        ),
    ]
    session.add_all(projects)
    await session.flush()

    for project in projects:
        session.add(
            ProjectMedia(
                project_id=project.id,
                asset_type=MediaType.VIDEO,
                url=project.preview_video_url or "",
                alt_ru=f"Превью проекта {project.title_ru}",
                alt_en=f"{project.title_en} project preview",
                sort_order=1,
            )
        )
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
