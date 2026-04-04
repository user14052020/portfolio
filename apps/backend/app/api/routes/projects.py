from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user, require_admin
from app.db.session import get_db_session
from app.models import Project, User
from app.models.enums import RoleCode
from app.repositories.projects import projects_repository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.search import search_service
from app.utils.slug import build_slug


router = APIRouter(prefix="/projects", tags=["projects"])


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
    data["slug"] = data.get("slug") or build_slug(payload.title_en)
    project = await projects_repository.create(session, data)
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
    project = await projects_repository.get(session, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if data.get("title_en") and not data.get("slug"):
        data["slug"] = build_slug(data["title_en"])
    project = await projects_repository.update(session, project, data)
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
