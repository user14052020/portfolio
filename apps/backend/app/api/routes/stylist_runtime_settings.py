from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.models import SiteSettings, User
from app.schemas.stylist_runtime_settings import (
    StylistRuntimeSettingsRead,
    StylistRuntimeSettingsUpdate,
)
from app.services.stylist_runtime_settings import StylistRuntimeSettingsService


router = APIRouter(prefix="/stylist-runtime-settings", tags=["stylist-runtime-settings"])
runtime_settings_service = StylistRuntimeSettingsService()


@router.get("/", response_model=StylistRuntimeSettingsRead)
async def get_stylist_runtime_settings(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SiteSettings:
    settings = await runtime_settings_service.read(session)
    await session.commit()
    return settings


@router.put("/", response_model=StylistRuntimeSettingsRead)
async def update_stylist_runtime_settings(
    payload: StylistRuntimeSettingsUpdate,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SiteSettings:
    settings = await runtime_settings_service.update(session, payload=payload.model_dump())
    await session.commit()
    return settings
