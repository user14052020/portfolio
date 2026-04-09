"""add ingest job foundation tables

Revision ID: 202604090013
Revises: 202604090012
Create Date: 2026-04-10 00:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090013"
down_revision: str | None = "202604090012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_source_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("page_kind", sa.String(length=32), nullable=False, server_default="style"),
        sa.Column("remote_page_id", sa.Integer(), nullable=True),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_revision_id", sa.Integer(), nullable=True),
        sa.Column("latest_content_fingerprint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_pages")),
    )
    op.create_index(op.f("ix_style_source_pages_source_url"), "style_source_pages", ["source_name", "page_url"], unique=True)
    op.create_index(op.f("ix_style_source_pages_source_kind"), "style_source_pages", ["source_name", "page_kind"], unique=False)
    op.create_index(
        op.f("ix_style_source_pages_source_remote_page"),
        "style_source_pages",
        ["source_name", "remote_page_id"],
        unique=False,
    )
    op.alter_column("style_source_pages", "page_kind", server_default=None)

    op.create_table(
        "style_source_page_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=False),
        sa.Column("fetch_mode", sa.String(length=32), nullable=False),
        sa.Column("remote_revision_id", sa.Integer(), nullable=True),
        sa.Column("content_fingerprint", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=False),
        sa.Column("raw_wikitext", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_source_pages.id"],
            name=op.f("fk_style_source_page_versions_source_page_id_style_source_pages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_page_versions")),
    )
    op.create_index(
        op.f("ix_style_source_page_versions_page_revision"),
        "style_source_page_versions",
        ["source_page_id", "remote_revision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_source_page_versions_page_fingerprint"),
        "style_source_page_versions",
        ["source_page_id", "content_fingerprint"],
        unique=False,
    )

    op.create_table(
        "style_ingest_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_page_id", sa.Integer(), nullable=True),
        sa.Column("source_page_version_id", sa.Integer(), nullable=True),
        sa.Column("last_error_class", sa.Text(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_source_pages.id"],
            name=op.f("fk_style_ingest_jobs_source_page_id_style_source_pages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_page_version_id"],
            ["style_source_page_versions.id"],
            name=op.f("fk_style_ingest_jobs_source_page_version_id_style_source_page_versions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_ingest_jobs")),
    )
    op.create_index(op.f("ix_style_ingest_jobs_dedupe_key"), "style_ingest_jobs", ["dedupe_key"], unique=True)
    op.create_index(
        op.f("ix_style_ingest_jobs_status_available"),
        "style_ingest_jobs",
        ["status", "available_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_ingest_jobs_source_type_status"),
        "style_ingest_jobs",
        ["source_name", "job_type", "status"],
        unique=False,
    )
    op.alter_column("style_ingest_jobs", "status", server_default=None)
    op.alter_column("style_ingest_jobs", "priority", server_default=None)
    op.alter_column("style_ingest_jobs", "attempt_count", server_default=None)

    op.create_table(
        "style_ingest_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["style_ingest_jobs.id"],
            name=op.f("fk_style_ingest_attempts_job_id_style_ingest_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_ingest_attempts")),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_style_ingest_attempts_job_attempt_number"),
    )
    op.create_index(
        op.f("ix_style_ingest_attempts_job_status"),
        "style_ingest_attempts",
        ["job_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_style_ingest_attempts_job_status"), table_name="style_ingest_attempts")
    op.drop_table("style_ingest_attempts")
    op.drop_index(op.f("ix_style_ingest_jobs_source_type_status"), table_name="style_ingest_jobs")
    op.drop_index(op.f("ix_style_ingest_jobs_status_available"), table_name="style_ingest_jobs")
    op.drop_index(op.f("ix_style_ingest_jobs_dedupe_key"), table_name="style_ingest_jobs")
    op.drop_table("style_ingest_jobs")
    op.drop_index(op.f("ix_style_source_page_versions_page_fingerprint"), table_name="style_source_page_versions")
    op.drop_index(op.f("ix_style_source_page_versions_page_revision"), table_name="style_source_page_versions")
    op.drop_table("style_source_page_versions")
    op.drop_index(op.f("ix_style_source_pages_source_remote_page"), table_name="style_source_pages")
    op.drop_index(op.f("ix_style_source_pages_source_kind"), table_name="style_source_pages")
    op.drop_index(op.f("ix_style_source_pages_source_url"), table_name="style_source_pages")
    op.drop_table("style_source_pages")
