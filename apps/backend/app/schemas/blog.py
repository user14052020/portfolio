from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import BlogPostType
from app.schemas.common import TimestampedRead


class BlogCategoryRead(TimestampedRead):
    id: int
    slug: str
    name_ru: str
    name_en: str


class BlogPostBase(BaseModel):
    slug: str | None = None
    title_ru: str
    title_en: str
    excerpt_ru: str
    excerpt_en: str
    content_ru: str
    content_en: str
    cover_image: str | None = None
    video_url: str | None = None
    post_type: BlogPostType
    tags: list[str] = Field(default_factory=list)
    seo_title_ru: str | None = None
    seo_title_en: str | None = None
    seo_description_ru: str | None = None
    seo_description_en: str | None = None
    page_scene_key: str | None = None
    is_published: bool = True
    published_at: datetime | None = None
    category_id: int | None = None


class BlogPostCreate(BlogPostBase):
    pass


class BlogPostUpdate(BlogPostBase):
    title_ru: str | None = None
    title_en: str | None = None
    excerpt_ru: str | None = None
    excerpt_en: str | None = None
    content_ru: str | None = None
    content_en: str | None = None
    post_type: BlogPostType | None = None


class BlogPostRead(TimestampedRead):
    id: int
    slug: str
    title_ru: str
    title_en: str
    excerpt_ru: str
    excerpt_en: str
    content_ru: str
    content_en: str
    cover_image: str | None = None
    video_url: str | None = None
    post_type: BlogPostType
    tags: list[str]
    seo_title_ru: str | None = None
    seo_title_en: str | None = None
    seo_description_ru: str | None = None
    seo_description_en: str | None = None
    page_scene_key: str | None = None
    is_published: bool
    published_at: datetime | None = None
    category: BlogCategoryRead | None = None

