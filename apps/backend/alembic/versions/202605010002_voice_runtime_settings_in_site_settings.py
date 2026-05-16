"""add voice runtime settings to site settings

Revision ID: 202605010002
Revises: 202605010001
Create Date: 2026-05-01 00:00:02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202605010002"
down_revision = "202605010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column(
            "voice_runtime_flags_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.alter_column("site_settings", "voice_runtime_flags_json", server_default=None)


def downgrade() -> None:
    op.drop_column("site_settings", "voice_runtime_flags_json")
