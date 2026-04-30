"""add knowledge runtime settings to site settings

Revision ID: 202605010001
Revises: 202604210001
Create Date: 2026-05-01 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202605010001"
down_revision: str | None = "202604210001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column(
            "knowledge_runtime_flags_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "site_settings",
        sa.Column(
            "knowledge_provider_priorities_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("site_settings", "knowledge_provider_priorities_json")
    op.drop_column("site_settings", "knowledge_runtime_flags_json")
