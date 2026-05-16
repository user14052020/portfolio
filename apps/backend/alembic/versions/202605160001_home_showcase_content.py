"""add editable home showcase content

Revision ID: 202605160001
Revises: 202604210001
Create Date: 2026-05-16 13:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202605160001"
down_revision: str | None = "202604210001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column(
            "homepage_content",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "site_settings",
        sa.Column(
            "chat_bot_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "showcase_meta",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "showcase_meta")
    op.drop_column("site_settings", "chat_bot_enabled")
    op.drop_column("site_settings", "homepage_content")
