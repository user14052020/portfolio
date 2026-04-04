from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user, require_admin
from app.db.session import get_db_session
from app.models import BlogPost, User
from app.models.enums import BlogPostType, RoleCode
from app.repositories.blog_posts import blog_posts_repository
from app.schemas.blog import BlogPostCreate, BlogPostRead, BlogPostUpdate
from app.services.search import search_service
from app.utils.slug import build_slug


router = APIRouter(prefix="/blog-posts", tags=["blog-posts"])


@router.get("/", response_model=list[BlogPostRead])
async def list_blog_posts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    q: str | None = None,
    category_slug: str | None = None,
    post_type: BlogPostType | None = None,
    include_drafts: bool = False,
) -> list[BlogPost]:
    if include_drafts and (not current_user or current_user.role.name != RoleCode.ADMIN.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required for drafts")
    return await blog_posts_repository.list_posts(
        session,
        only_published=not include_drafts,
        q=q,
        category_slug=category_slug,
        post_type=post_type,
    )


@router.get("/{slug}", response_model=BlogPostRead)
async def get_blog_post(slug: str, session: Annotated[AsyncSession, Depends(get_db_session)]) -> BlogPost:
    post = await blog_posts_repository.get_by_slug(session, slug)
    if not post or not post.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post


@router.post("/", response_model=BlogPostRead)
async def create_blog_post(
    payload: BlogPostCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> BlogPost:
    data = payload.model_dump()
    data["slug"] = data.get("slug") or build_slug(payload.title_en)
    post = await blog_posts_repository.create(session, data)
    await session.commit()
    await search_service.index_blog_post(post)
    return await blog_posts_repository.get_by_slug(session, post.slug)  # type: ignore[return-value]


@router.put("/{post_id}", response_model=BlogPostRead)
async def update_blog_post(
    post_id: int,
    payload: BlogPostUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> BlogPost:
    post = await blog_posts_repository.get(session, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if data.get("title_en") and not data.get("slug"):
        data["slug"] = build_slug(data["title_en"])
    post = await blog_posts_repository.update(session, post, data)
    await session.commit()
    await search_service.index_blog_post(post)
    return await blog_posts_repository.get_by_slug(session, post.slug)  # type: ignore[return-value]


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog_post(
    post_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(require_admin)],
) -> Response:
    post = await blog_posts_repository.get(session, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    slug = post.slug
    await blog_posts_repository.delete(session, post)
    await session.commit()
    await search_service.delete_document("blog_posts", slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
