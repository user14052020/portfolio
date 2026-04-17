from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db_session
from app.ingestion.styles.runtime_settings_service import StyleIngestionRuntimeSettingsService
from app.models import StyleIngestionRuntimeSettings, User
from app.schemas.style_ingestion_settings import (
    StyleIngestionRuntimeSettingsRead,
    StyleIngestionRuntimeSettingsUpdate,
)


router = APIRouter(prefix="/style-ingestion-settings", tags=["style-ingestion-settings"])
runtime_settings_service = StyleIngestionRuntimeSettingsService()


@router.get("/{source_name}", response_model=StyleIngestionRuntimeSettingsRead)
async def get_style_ingestion_settings(
    source_name: str,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StyleIngestionRuntimeSettings:
    settings = await runtime_settings_service.read(session, source_name=source_name)
    await session.commit()
    return settings


@router.put("/{source_name}", response_model=StyleIngestionRuntimeSettingsRead)
async def update_style_ingestion_settings(
    source_name: str,
    payload: StyleIngestionRuntimeSettingsUpdate,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StyleIngestionRuntimeSettings:
    settings = await runtime_settings_service.update(
        session,
        source_name=source_name,
        payload=payload.model_dump(),
    )
    await session.commit()
    return settings
