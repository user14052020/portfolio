from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BlogPost
from app.models.enums import BlogPostType
from app.repositories.base import BaseRepository


class BlogPostsRepository(BaseRepository[BlogPost]):
    def __init__(self) -> None:
        super().__init__(BlogPost)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> BlogPost | None:
        result = await session.execute(select(BlogPost).options(joinedload(BlogPost.category)).where(BlogPost.slug == slug))
        return result.scalar_one_or_none()

    async def list_posts(
        self,
        session: AsyncSession,
        *,
        only_published: bool,
        q: str | None = None,
        category_slug: str | None = None,
        post_type: BlogPostType | None = None,
    ) -> list[BlogPost]:
        statement = select(BlogPost).options(joinedload(BlogPost.category)).order_by(BlogPost.published_at.desc().nullslast())
        if only_published:
            statement = statement.where(BlogPost.is_published.is_(True))
        if q:
            pattern = f"%{q}%"
            statement = statement.where(
                or_(
                    BlogPost.title_ru.ilike(pattern),
                    BlogPost.title_en.ilike(pattern),
                    BlogPost.excerpt_ru.ilike(pattern),
                    BlogPost.excerpt_en.ilike(pattern),
                )
            )
        if category_slug:
            statement = statement.where(BlogPost.category.has(slug=category_slug))
        if post_type:
            statement = statement.where(BlogPost.post_type == post_type)
        result = await session.execute(statement)
        return list(result.scalars().unique().all())


blog_posts_repository = BlogPostsRepository()

