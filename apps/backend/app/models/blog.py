from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import BlogPostType, sql_enum
from app.models.mixins import Base, TimestampedMixin


class BlogCategory(Base, TimestampedMixin):
    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name_ru: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))

    posts = relationship("BlogPost", back_populates="category")


class BlogPost(Base, TimestampedMixin):
    __tablename__ = "blog_posts"
    __table_args__ = (Index("ix_blog_posts_published_at", "is_published", "published_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title_ru: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))
    excerpt_ru: Mapped[str] = mapped_column(Text)
    excerpt_en: Mapped[str] = mapped_column(Text)
    content_ru: Mapped[str] = mapped_column(Text)
    content_en: Mapped[str] = mapped_column(Text)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    post_type: Mapped[BlogPostType] = mapped_column(sql_enum(BlogPostType, name="blog_post_type"))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    seo_title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_scene_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("blog_categories.id"), nullable=True, index=True)

    category = relationship("BlogCategory", back_populates="posts")
