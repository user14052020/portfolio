"""add source fetch logs table

Revision ID: 202604090011
Revises: 202604090010
Create Date: 2026-04-09 23:59:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090011"
down_revision: str | None = "202604090010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_source_fetch_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("fetch_mode", sa.String(length=32), nullable=False),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_headers_json", sa.JSON(), nullable=True),
        sa.Column("response_size_bytes", sa.Integer(), nullable=True),
        sa.Column("response_content_type", sa.Text(), nullable=True),
        sa.Column("response_body_hash", sa.Text(), nullable=True),
        sa.Column("response_body_preview", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_fetch_logs")),
    )
    op.create_index(
        op.f("ix_style_source_fetch_logs_source_name_fetched_at"),
        "style_source_fetch_logs",
        ["source_name", "fetched_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_source_fetch_logs_fetch_mode"),
        "style_source_fetch_logs",
        ["fetch_mode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_source_fetch_logs_request_url"),
        "style_source_fetch_logs",
        ["request_url"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_style_source_fetch_logs_request_url"), table_name="style_source_fetch_logs")
    op.drop_index(op.f("ix_style_source_fetch_logs_fetch_mode"), table_name="style_source_fetch_logs")
    op.drop_index(op.f("ix_style_source_fetch_logs_source_name_fetched_at"), table_name="style_source_fetch_logs")
    op.drop_table("style_source_fetch_logs")
