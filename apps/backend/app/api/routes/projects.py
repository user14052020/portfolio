from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.api.deps import get_optional_current_user, require_admin
from app.db.session import get_db_session
from app.models import Project, ProjectMedia, User
from app.models.enums import RoleCode
from app.repositories.projects import projects_repository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.search import search_service
from app.utils.slug import build_slug


router = APIRouter(prefix="/projects", tags=["projects"])

PROJECT_NULLABLE_UPDATE_FIELDS = {
    "cover_image",
    "preview_video_url",
    "repository_url",
    "live_url",
    "page_scene_key",
    "seo_title_ru",
    "seo_title_en",
    "seo_description_ru",
    "seo_description_en",
}


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    q: str | None = None,
    featured_only: bool = False,
    include_drafts: bool = False,
) -> list[Project]:
    if include_drafts and (not current_user or current_user.role.name != RoleCode.ADMIN.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required for drafts")
    return await projects_repository.list_projects(
        session,
        only_published=not include_drafts,
        q=q,
        featured_only=featured_only,
    )


@router.get("/{slug}", response_model=ProjectRead)
async def get_project(slug: str, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Project:
    project = await projects_repository.get_by_slug(session, slug)
    if not project or not project.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/", response_model=ProjectRead)
async def create_project(
    payload: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> Project:
    data = payload.model_dump()
    media_items = data.pop("media_items", [])
    data["slug"] = data.get("slug") or build_slug(payload.title_en)
    project = await projects_repository.create(session, data)
    await sync_project_media_items(session, project, media_items)
    await session.commit()
    await search_service.index_project(project)
    return await projects_repository.get_by_slug(session, project.slug)  # type: ignore[return-value]


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> Project:
    project = await projects_repository.get_by_id_with_media(session, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    data = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or key in PROJECT_NULLABLE_UPDATE_FIELDS
    }
    media_items = data.pop("media_items", None)
    if data.get("title_en") and not data.get("slug"):
        data["slug"] = build_slug(data["title_en"])
    for key, value in data.items():
        setattr(project, key, value)
    if media_items is not None:
        await sync_project_media_items(session, project, media_items)
    await session.flush()
    await session.commit()
    await search_service.index_project(project)
    return await projects_repository.get_by_slug(session, project.slug)  # type: ignore[return-value]


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> Response:
    project = await projects_repository.get(session, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    slug = project.slug
    await projects_repository.delete(session, project)
    await session.commit()
    await search_service.delete_document("projects", slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def sync_project_media_items(session: AsyncSession, project: Project, media_items: list[dict]) -> None:
    await session.execute(sa.delete(ProjectMedia).where(ProjectMedia.project_id == project.id))
    attributes.set_committed_value(project, "media_items", [])
    next_media_items = [
        ProjectMedia(
            project_id=project.id,
            asset_type=item["asset_type"],
            url=item["url"],
            alt_ru=item.get("alt_ru"),
            alt_en=item.get("alt_en"),
            sort_order=item.get("sort_order", index),
        )
        for index, item in enumerate(media_items)
        if item.get("url")
    ]
    session.add_all(next_media_items)
    await session.flush()
    attributes.set_committed_value(project, "media_items", next_media_items)
