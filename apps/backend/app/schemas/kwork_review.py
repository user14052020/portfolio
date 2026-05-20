from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class KworkReviewRead(TimestampedRead):
    id: int
    external_id: str
    source_url: str
    source_platform: str
    review_type: str
    author_name: str
    author_url: str | None = None
    author_avatar_url: str | None = None
    project_title: str | None = None
    project_url: str | None = None
    rating: int
    text: str
    reviewed_at: datetime | None = None
    time_ago: str | None = None
    sort_order: int
    is_published: bool


class KworkReviewUpdate(BaseModel):
    author_name: str | None = None
    author_url: str | None = None
    project_title: str | None = None
    project_url: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None


class KworkReviewsPage(BaseModel):
    items: list[KworkReviewRead]
    total: int
    offset: int
    limit: int


class KworkReviewsSyncRequest(BaseModel):
    source_url: str = "https://kwork.ru/user/portfolio-dev"
    replace: bool = True
    limit: int = Field(default=100, ge=1, le=200)


class KworkReviewsSyncResult(BaseModel):
    source_url: str
    imported: int
    total: int
    page: KworkReviewsPage
