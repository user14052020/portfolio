"""add run status and checkpoint to style_ingest_runs

Revision ID: 202604090009
Revises: 202604090008
Create Date: 2026-04-09 23:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090009"
down_revision: str | None = "202604090008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "style_ingest_runs",
        sa.Column("run_status", sa.String(length=32), nullable=False, server_default="running"),
    )
    op.add_column(
        "style_ingest_runs",
        sa.Column("checkpoint_json", sa.JSON(), nullable=True),
    )
    op.alter_column("style_ingest_runs", "run_status", server_default=None)


def downgrade() -> None:
    op.drop_column("style_ingest_runs", "checkpoint_json")
    op.drop_column("style_ingest_runs", "run_status")
