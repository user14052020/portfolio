"""add source fetch state table

Revision ID: 202604090010
Revises: 202604090009
Create Date: 2026-04-09 23:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090010"
down_revision: str | None = "202604090009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_source_fetch_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_empty_body_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_empty_bodies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_error_class", sa.Text(), nullable=True),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_min_interval_sec", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_fetch_states")),
    )
    op.create_index(
        op.f("ix_style_source_fetch_states_source_name"),
        "style_source_fetch_states",
        ["source_name"],
        unique=True,
    )
    op.create_index(
        op.f("ix_style_source_fetch_states_mode"),
        "style_source_fetch_states",
        ["mode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_source_fetch_states_next_allowed_at"),
        "style_source_fetch_states",
        ["next_allowed_at"],
        unique=False,
    )
    op.alter_column("style_source_fetch_states", "mode", server_default=None)
    op.alter_column("style_source_fetch_states", "consecutive_empty_bodies", server_default=None)
    op.alter_column("style_source_fetch_states", "current_min_interval_sec", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_style_source_fetch_states_next_allowed_at"), table_name="style_source_fetch_states")
    op.drop_index(op.f("ix_style_source_fetch_states_mode"), table_name="style_source_fetch_states")
    op.drop_index(op.f("ix_style_source_fetch_states_source_name"), table_name="style_source_fetch_states")
    op.drop_table("style_source_fetch_states")
