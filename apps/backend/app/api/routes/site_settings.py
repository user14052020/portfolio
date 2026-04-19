from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import SiteSettings, User
from app.repositories.site_settings import site_settings_repository
from app.schemas.site_settings import SiteSettingsRead, SiteSettingsUpdate


router = APIRouter(prefix="/site-settings", tags=["site-settings"])


@router.get("/", response_model=SiteSettingsRead)
async def get_site_settings(session: Annotated[AsyncSession, Depends(get_db_session)]) -> SiteSettings:
    settings = await site_settings_repository.get_or_create_singleton(session)
    await session.commit()
    return settings


@router.put("/", response_model=SiteSettingsRead)
async def update_site_settings(
    payload: SiteSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> SiteSettings:
    settings = await site_settings_repository.get_or_create_singleton(session)
    settings = await site_settings_repository.update(session, settings, payload.model_dump())
    await session.commit()
    return settings
