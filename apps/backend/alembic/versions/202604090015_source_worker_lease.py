"""add source worker lease fields

Revision ID: 202604090015
Revises: 202604090014
Create Date: 2026-04-10 01:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090015"
down_revision: str | None = "202604090014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("style_source_fetch_states", sa.Column("worker_lease_owner", sa.Text(), nullable=True))
    op.add_column("style_source_fetch_states", sa.Column("worker_lease_acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("style_source_fetch_states", sa.Column("worker_lease_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("style_source_fetch_states", sa.Column("worker_lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_style_source_fetch_states_worker_lease_expires_at"),
        "style_source_fetch_states",
        ["worker_lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_style_source_fetch_states_worker_lease_expires_at"),
        table_name="style_source_fetch_states",
    )
    op.drop_column("style_source_fetch_states", "worker_lease_expires_at")
    op.drop_column("style_source_fetch_states", "worker_lease_heartbeat_at")
    op.drop_column("style_source_fetch_states", "worker_lease_acquired_at")
    op.drop_column("style_source_fetch_states", "worker_lease_owner")
