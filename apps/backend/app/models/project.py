from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import MediaType, sql_enum
from app.models.mixins import Base, TimestampedMixin


class Project(Base, TimestampedMixin):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_published_sort", "is_published", "sort_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title_ru: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))
    summary_ru: Mapped[str] = mapped_column(Text)
    summary_en: Mapped[str] = mapped_column(Text)
    description_ru: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    stack: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preview_video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_scene_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    seo_title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    media_items = relationship("ProjectMedia", back_populates="project", cascade="all, delete-orphan")


class ProjectMedia(Base, TimestampedMixin):
    __tablename__ = "project_media"
    __table_args__ = (Index("ix_project_media_project_sort", "project_id", "sort_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    asset_type: Mapped[MediaType] = mapped_column(sql_enum(MediaType, name="media_type"))
    url: Mapped[str] = mapped_column(String(512))
    alt_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alt_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    project = relationship("Project", back_populates="media_items")
