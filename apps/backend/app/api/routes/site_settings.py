from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import SiteSettings, User
from app.repositories.site_settings import site_settings_repository
from app.schemas.site_settings import SiteSettingsRead, SiteSettingsUpdate


router = APIRouter(prefix="/site-settings", tags=["site-settings"])


def _default_settings_payload() -> dict:
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
        "socials": {"telegram": "https://t.me/example", "github": "https://github.com/example"},
        "skills": ["FastAPI", "Next.js", "ComfyUI", "Motion Design", "Three.js"],
    }


@router.get("/", response_model=SiteSettingsRead)
async def get_site_settings(session: Annotated[AsyncSession, Depends(get_db_session)]) -> SiteSettings:
    settings = await site_settings_repository.get_singleton(session)
    if not settings:
        settings = await site_settings_repository.create(session, _default_settings_payload())
        await session.commit()
    return settings


@router.put("/", response_model=SiteSettingsRead)
async def update_site_settings(
    payload: SiteSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> SiteSettings:
    settings = await site_settings_repository.get_singleton(session)
    if not settings:
        settings = await site_settings_repository.create(session, payload.model_dump())
    else:
        settings = await site_settings_repository.update(session, settings, payload.model_dump())
    await session.commit()
    return settings
