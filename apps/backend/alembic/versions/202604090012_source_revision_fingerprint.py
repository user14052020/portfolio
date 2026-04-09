"""add source revision fingerprint fields

Revision ID: 202604090012
Revises: 202604090011
Create Date: 2026-04-10 00:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604090012"
down_revision: str | None = "202604090011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("style_sources", sa.Column("fetch_mode", sa.String(length=32), nullable=True))
    op.add_column("style_sources", sa.Column("remote_page_id", sa.Integer(), nullable=True))
    op.add_column("style_sources", sa.Column("remote_revision_id", sa.Integer(), nullable=True))
    op.add_column("style_sources", sa.Column("content_fingerprint", sa.Text(), nullable=True))
    op.add_column("style_sources", sa.Column("raw_wikitext", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_style_sources_site_page_id"),
        "style_sources",
        ["source_site", "remote_page_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_sources_site_revision_id"),
        "style_sources",
        ["source_site", "remote_revision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_style_sources_site_revision_id"), table_name="style_sources")
    op.drop_index(op.f("ix_style_sources_site_page_id"), table_name="style_sources")
    op.drop_column("style_sources", "raw_wikitext")
    op.drop_column("style_sources", "content_fingerprint")
    op.drop_column("style_sources", "remote_revision_id")
    op.drop_column("style_sources", "remote_page_id")
    op.drop_column("style_sources", "fetch_mode")
