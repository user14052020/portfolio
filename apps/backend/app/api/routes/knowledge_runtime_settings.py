from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.application.knowledge.services.knowledge_providers_registry import DefaultKnowledgeProvidersRegistry
from app.db.session import get_db_session
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.infrastructure.knowledge.style_distilled_knowledge_provider import StyleDistilledKnowledgeProvider
from app.models import User
from app.schemas.knowledge_runtime_settings import (
    KnowledgeRuntimeDiagnosticsRead,
    KnowledgeRuntimeSettingsRead,
    KnowledgeRuntimeSettingsUpdate,
)
from app.services.knowledge_runtime_settings import (
    DatabaseKnowledgeRuntimeSettingsProvider,
    KnowledgeRuntimeSettingsService,
)


router = APIRouter(prefix="/knowledge-runtime-settings", tags=["knowledge-runtime-settings"])
knowledge_runtime_settings_service = KnowledgeRuntimeSettingsService()


@router.get("/", response_model=KnowledgeRuntimeSettingsRead)
async def get_knowledge_runtime_settings(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeRuntimeSettingsRead:
    site_settings = await knowledge_runtime_settings_service.read_site_settings(session)
    runtime_settings = await knowledge_runtime_settings_service.read(session)
    await session.commit()
    return KnowledgeRuntimeSettingsRead(
        id=site_settings.id,
        created_at=site_settings.created_at,
        updated_at=site_settings.updated_at,
        **runtime_settings.model_dump(mode="json"),
    )


@router.put("/", response_model=KnowledgeRuntimeSettingsRead)
async def update_knowledge_runtime_settings(
    payload: KnowledgeRuntimeSettingsUpdate,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeRuntimeSettingsRead:
    runtime_settings = await knowledge_runtime_settings_service.update(
        session,
        payload=payload.model_dump(),
    )
    site_settings = await knowledge_runtime_settings_service.read_site_settings(session)
    await session.commit()
    return KnowledgeRuntimeSettingsRead(
        id=site_settings.id,
        created_at=site_settings.created_at,
        updated_at=site_settings.updated_at,
        **runtime_settings.model_dump(mode="json"),
    )


@router.get("/diagnostics", response_model=KnowledgeRuntimeDiagnosticsRead)
async def get_knowledge_runtime_diagnostics(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeRuntimeDiagnosticsRead:
    provider = DatabaseKnowledgeRuntimeSettingsProvider(
        session=session,
        service=knowledge_runtime_settings_service,
    )
    style_catalog_repository = DatabaseStyleCatalogRepository(session)
    registry = DefaultKnowledgeProvidersRegistry(
        providers=[
            StyleDistilledKnowledgeProvider(
                projection_repository=style_catalog_repository,
            )
        ],
        runtime_settings_provider=provider,
    )
    settings = await knowledge_runtime_settings_service.read(session)
    providers = await registry.get_enabled_runtime_providers()
    await session.commit()
    return KnowledgeRuntimeDiagnosticsRead(
        runtime_flags=settings.runtime_flags().model_dump(mode="json"),
        provider_priorities=settings.normalized_provider_priorities(),
        enabled_runtime_providers=[
            {
                "code": item.config.code,
                "name": item.config.name,
                "provider_type": item.config.provider_type,
                "priority": settings.normalized_provider_priorities().get(
                    item.config.code.strip().lower(),
                    item.config.priority,
                ),
                "runtime_roles": list(item.config.runtime_roles),
            }
            for item in providers
        ],
    )
