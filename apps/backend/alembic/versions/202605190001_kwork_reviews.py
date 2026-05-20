"""add kwork reviews

Revision ID: 202605190001
Revises: ce5540d45d6b
Create Date: 2026-05-19 21:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202605190001"
down_revision: str | None = "ce5540d45d6b"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kwork_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("source_platform", sa.String(length=64), nullable=False, server_default="kwork"),
        sa.Column("review_type", sa.String(length=32), nullable=False, server_default="positive"),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("author_url", sa.String(length=512), nullable=True),
        sa.Column("author_avatar_url", sa.String(length=512), nullable=True),
        sa.Column("project_title", sa.String(length=255), nullable=True),
        sa.Column("project_url", sa.String(length=512), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_ago", sa.String(length=120), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kwork_reviews_external_id", "kwork_reviews", ["external_id"], unique=True)
    op.create_index(
        "ix_kwork_reviews_published_sort",
        "kwork_reviews",
        ["is_published", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kwork_reviews_published_sort", table_name="kwork_reviews")
    op.drop_index("ix_kwork_reviews_external_id", table_name="kwork_reviews")
    op.drop_table("kwork_reviews")
