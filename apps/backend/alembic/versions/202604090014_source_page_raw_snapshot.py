"""add raw sections and links snapshots to source pages

Revision ID: 202604090014
Revises: 202604090013
Create Date: 2026-04-10 00:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090014"
down_revision: str | None = "202604090013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "style_source_page_versions",
        sa.Column("raw_sections_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "style_source_page_versions",
        sa.Column("raw_links_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.alter_column("style_source_page_versions", "raw_sections_json", server_default=None)
    op.alter_column("style_source_page_versions", "raw_links_json", server_default=None)

    op.add_column(
        "style_sources",
        sa.Column("raw_links_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.alter_column("style_sources", "raw_links_json", server_default=None)


def downgrade() -> None:
    op.drop_column("style_sources", "raw_links_json")
    op.drop_column("style_source_page_versions", "raw_links_json")
    op.drop_column("style_source_page_versions", "raw_sections_json")
