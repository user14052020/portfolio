"""Initial schema

Revision ID: 202603300001
Revises:
Create Date: 2026-03-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202603300001"
down_revision = None
branch_labels = None
depends_on = None


media_type = postgresql.ENUM("image", "video", "model3d", name="media_type", create_type=False)
asset_type = postgresql.ENUM("image", "video", "document", "model3d", name="asset_type", create_type=False)
blog_post_type = postgresql.ENUM("article", "video", name="blog_post_type", create_type=False)
contact_request_status = postgresql.ENUM(
    "new", "in_progress", "closed", name="contact_request_status", create_type=False
)
generation_provider = postgresql.ENUM("comfyui", "mock", name="generation_provider", create_type=False)
generation_status = postgresql.ENUM(
    "pending", "queued", "running", "completed", "failed", name="generation_status", create_type=False
)
chat_message_role = postgresql.ENUM("user", "assistant", "system", name="chat_message_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    media_type.create(bind, checkfirst=True)
    asset_type.create(bind, checkfirst=True)
    blog_post_type.create(bind, checkfirst=True)
    contact_request_status.create(bind, checkfirst=True)
    generation_provider.create(bind, checkfirst=True)
    generation_status.create(bind, checkfirst=True)
    chat_message_role.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=False)

    op.create_table(
        "blog_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_blog_categories_slug"),
    )
    op.create_index("ix_blog_categories_slug", "blog_categories", ["slug"], unique=False)

    op.create_table(
        "contact_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("source_page", sa.String(length=120), nullable=True),
        sa.Column("status", contact_request_status, nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contact_requests_email", "contact_requests", ["email"], unique=False)

    op.create_table(
        "page_scenes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_key", sa.String(length=120), nullable=False),
        sa.Column("scene_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("page_key", name="uq_page_scenes_page_key"),
    )
    op.create_index("ix_page_scenes_page_key", "page_scenes", ["page_key"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title_ru", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("summary_ru", sa.Text(), nullable=False),
        sa.Column("summary_en", sa.Text(), nullable=False),
        sa.Column("description_ru", sa.Text(), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("stack", sa.JSON(), nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("preview_video_url", sa.String(length=512), nullable=True),
        sa.Column("repository_url", sa.String(length=512), nullable=True),
        sa.Column("live_url", sa.String(length=512), nullable=True),
        sa.Column("page_scene_key", sa.String(length=120), nullable=True),
        sa.Column("seo_title_ru", sa.String(length=255), nullable=True),
        sa.Column("seo_title_en", sa.String(length=255), nullable=True),
        sa.Column("seo_description_ru", sa.Text(), nullable=True),
        sa.Column("seo_description_en", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_projects_slug"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=False)
    op.create_index("ix_projects_sort_order", "projects", ["sort_order"], unique=False)
    op.create_index("ix_projects_published_sort", "projects", ["is_published", "sort_order"], unique=False)

    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brand_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("hero_title_ru", sa.String(length=255), nullable=False),
        sa.Column("hero_title_en", sa.String(length=255), nullable=False),
        sa.Column("hero_subtitle_ru", sa.Text(), nullable=False),
        sa.Column("hero_subtitle_en", sa.Text(), nullable=False),
        sa.Column("about_title_ru", sa.String(length=255), nullable=False),
        sa.Column("about_title_en", sa.String(length=255), nullable=False),
        sa.Column("about_text_ru", sa.Text(), nullable=False),
        sa.Column("about_text_en", sa.Text(), nullable=False),
        sa.Column("socials", sa.JSON(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_users_role_id_roles"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)

    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title_ru", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("excerpt_ru", sa.Text(), nullable=False),
        sa.Column("excerpt_en", sa.Text(), nullable=False),
        sa.Column("content_ru", sa.Text(), nullable=False),
        sa.Column("content_en", sa.Text(), nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("video_url", sa.String(length=512), nullable=True),
        sa.Column("post_type", blog_post_type, nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("seo_title_ru", sa.String(length=255), nullable=True),
        sa.Column("seo_title_en", sa.String(length=255), nullable=True),
        sa.Column("seo_description_ru", sa.Text(), nullable=True),
        sa.Column("seo_description_en", sa.Text(), nullable=True),
        sa.Column("page_scene_key", sa.String(length=120), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["blog_categories.id"], name="fk_blog_posts_category_id_blog_categories"),
        sa.UniqueConstraint("slug", name="uq_blog_posts_slug"),
    )
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=False)
    op.create_index("ix_blog_posts_category_id", "blog_posts", ["category_id"], unique=False)
    op.create_index("ix_blog_posts_published_at", "blog_posts", ["is_published", "published_at"], unique=False)

    op.create_table(
        "project_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", media_type, nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("alt_ru", sa.String(length=255), nullable=True),
        sa.Column("alt_en", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_project_media_project_id_projects", ondelete="CASCADE"),
    )
    op.create_index("ix_project_media_project_sort", "project_media", ["project_id", "sort_order"], unique=False)

    op.create_table(
        "uploaded_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("public_url", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("storage_backend", sa.String(length=50), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("related_entity", sa.String(length=120), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], name="fk_uploaded_assets_uploaded_by_id_users"),
        sa.UniqueConstraint("storage_path", name="uq_uploaded_assets_storage_path"),
    )
    op.create_index("ix_uploaded_assets_uploaded_by_id", "uploaded_assets", ["uploaded_by_id"], unique=False)

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=True),
        sa.Column("provider", generation_provider, nullable=False, server_default="comfyui"),
        sa.Column("status", generation_status, nullable=False, server_default="pending"),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("recommendation_ru", sa.Text(), nullable=False),
        sa.Column("recommendation_en", sa.Text(), nullable=False),
        sa.Column("input_asset_id", sa.Integer(), nullable=True),
        sa.Column("result_url", sa.String(length=512), nullable=True),
        sa.Column("external_job_id", sa.String(length=120), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body_height_cm", sa.Integer(), nullable=True),
        sa.Column("body_weight_kg", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provider_payload", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["input_asset_id"], ["uploaded_assets.id"], name="fk_generation_jobs_input_asset_id_uploaded_assets"),
        sa.UniqueConstraint("public_id", name="uq_generation_jobs_public_id"),
    )
    op.create_index("ix_generation_jobs_public_id", "generation_jobs", ["public_id"], unique=False)
    op.create_index("ix_generation_jobs_external_job_id", "generation_jobs", ["external_job_id"], unique=False)
    op.create_index("ix_generation_jobs_input_asset_id", "generation_jobs", ["input_asset_id"], unique=False)
    op.create_index("ix_generation_jobs_session_id", "generation_jobs", ["session_id"], unique=False)
    op.create_index("ix_generation_jobs_status_created_at", "generation_jobs", ["status", "created_at"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("role", chat_message_role, nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generation_job_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_asset_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["generation_job_id"], ["generation_jobs.id"], name="fk_chat_messages_generation_job_id_generation_jobs"),
        sa.ForeignKeyConstraint(["uploaded_asset_id"], ["uploaded_assets.id"], name="fk_chat_messages_uploaded_asset_id_uploaded_assets"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"], unique=False)
    op.create_index("ix_chat_messages_session_created", "chat_messages", ["session_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_generation_jobs_status_created_at", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_session_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_input_asset_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_external_job_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_public_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")

    op.drop_index("ix_uploaded_assets_uploaded_by_id", table_name="uploaded_assets")
    op.drop_table("uploaded_assets")

    op.drop_index("ix_project_media_project_sort", table_name="project_media")
    op.drop_table("project_media")

    op.drop_index("ix_blog_posts_published_at", table_name="blog_posts")
    op.drop_index("ix_blog_posts_category_id", table_name="blog_posts")
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_table("blog_posts")

    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_table("site_settings")

    op.drop_index("ix_projects_published_sort", table_name="projects")
    op.drop_index("ix_projects_sort_order", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_page_scenes_page_key", table_name="page_scenes")
    op.drop_table("page_scenes")

    op.drop_index("ix_contact_requests_email", table_name="contact_requests")
    op.drop_table("contact_requests")

    op.drop_index("ix_blog_categories_slug", table_name="blog_categories")
    op.drop_table("blog_categories")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")

    bind = op.get_bind()
    chat_message_role.drop(bind, checkfirst=True)
    generation_status.drop(bind, checkfirst=True)
    generation_provider.drop(bind, checkfirst=True)
    contact_request_status.drop(bind, checkfirst=True)
    blog_post_type.drop(bind, checkfirst=True)
    asset_type.drop(bind, checkfirst=True)
    media_type.drop(bind, checkfirst=True)
