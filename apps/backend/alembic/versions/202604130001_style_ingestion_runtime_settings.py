"""add style ingestion runtime settings

Revision ID: 202604130001
Revises: 202604090015
Create Date: 2026-04-13 20:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604130001"
down_revision: str | None = "202604090015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_ingestion_runtime_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("min_delay_seconds", sa.Float(), nullable=False),
        sa.Column("max_delay_seconds", sa.Float(), nullable=False),
        sa.Column("jitter_ratio", sa.Float(), nullable=False),
        sa.Column("empty_body_cooldown_min_seconds", sa.Float(), nullable=False),
        sa.Column("empty_body_cooldown_max_seconds", sa.Float(), nullable=False),
        sa.Column("retry_backoff_seconds", sa.Float(), nullable=False),
        sa.Column("retry_backoff_jitter_seconds", sa.Float(), nullable=False),
        sa.Column("worker_idle_sleep_seconds", sa.Float(), nullable=False),
        sa.Column("worker_lease_ttl_seconds", sa.Float(), nullable=False),
        sa.Column("worker_lease_heartbeat_interval_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_ingestion_runtime_settings")),
        sa.UniqueConstraint("source_name", name="uq_style_ingestion_runtime_settings_source_name"),
    )
    op.create_index(
        op.f("ix_style_ingestion_runtime_settings_source_name"),
        "style_ingestion_runtime_settings",
        ["source_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_style_ingestion_runtime_settings_source_name"),
        table_name="style_ingestion_runtime_settings",
    )
    op.drop_table("style_ingestion_runtime_settings")
