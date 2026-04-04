from pydantic import BaseModel, Field

from app.models.enums import MediaType
from app.schemas.common import TimestampedRead


class ProjectMediaRead(TimestampedRead):
    id: int
    asset_type: MediaType
    url: str
    alt_ru: str | None = None
    alt_en: str | None = None
    sort_order: int


class ProjectBase(BaseModel):
    slug: str | None = None
    title_ru: str
    title_en: str
    summary_ru: str
    summary_en: str
    description_ru: str
    description_en: str
    stack: list[str] = Field(default_factory=list)
    cover_image: str | None = None
    preview_video_url: str | None = None
    repository_url: str | None = None
    live_url: str | None = None
    page_scene_key: str | None = None
    seo_title_ru: str | None = None
    seo_title_en: str | None = None
    seo_description_ru: str | None = None
    seo_description_en: str | None = None
    sort_order: int = 0
    is_featured: bool = True
    is_published: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    title_ru: str | None = None
    title_en: str | None = None
    summary_ru: str | None = None
    summary_en: str | None = None
    description_ru: str | None = None
    description_en: str | None = None


class ProjectRead(TimestampedRead):
    id: int
    slug: str
    title_ru: str
    title_en: str
    summary_ru: str
    summary_en: str
    description_ru: str
    description_en: str
    stack: list[str]
    cover_image: str | None = None
    preview_video_url: str | None = None
    repository_url: str | None = None
    live_url: str | None = None
    page_scene_key: str | None = None
    seo_title_ru: str | None = None
    seo_title_en: str | None = None
    seo_description_ru: str | None = None
    seo_description_en: str | None = None
    sort_order: int
    is_featured: bool
    is_published: bool
    media_items: list[ProjectMediaRead] = Field(default_factory=list)

