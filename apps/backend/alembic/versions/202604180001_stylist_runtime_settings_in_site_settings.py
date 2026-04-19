"""add stylist runtime settings to site settings

Revision ID: 202604180001
Revises: 202604170001
Create Date: 2026-04-18 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604180001"
down_revision: str | None = "202604170001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column(
            "daily_generation_limit_non_admin",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
    )
    op.add_column(
        "site_settings",
        sa.Column(
            "daily_chat_seconds_limit_non_admin",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("600"),
        ),
    )
    op.add_column(
        "site_settings",
        sa.Column(
            "message_cooldown_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
    )
    op.add_column(
        "site_settings",
        sa.Column(
            "try_other_style_cooldown_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
    )


def downgrade() -> None:
    op.drop_column("site_settings", "try_other_style_cooldown_seconds")
    op.drop_column("site_settings", "message_cooldown_seconds")
    op.drop_column("site_settings", "daily_chat_seconds_limit_non_admin")
    op.drop_column("site_settings", "daily_generation_limit_non_admin")
