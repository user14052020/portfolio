"""Add assistant names to site settings

Revision ID: 202603300002
Revises: 202603300001
Create Date: 2026-03-30 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202603300002"
down_revision = "202603300001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column("assistant_name_ru", sa.String(length=255), nullable=False, server_default="Валентин"),
    )
    op.add_column(
        "site_settings",
        sa.Column("assistant_name_en", sa.String(length=255), nullable=False, server_default="Jose"),
    )
    op.alter_column("site_settings", "assistant_name_ru", server_default=None)
    op.alter_column("site_settings", "assistant_name_en", server_default=None)


def downgrade() -> None:
    op.drop_column("site_settings", "assistant_name_en")
    op.drop_column("site_settings", "assistant_name_ru")
