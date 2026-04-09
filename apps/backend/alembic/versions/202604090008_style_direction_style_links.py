"""style direction to canonical style links

Revision ID: 202604090008
Revises: 202604090007
Create Date: 2026-04-09 03:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090008"
down_revision: str | None = "202604090007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_direction_style_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_direction_id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("linked_via_match_id", sa.Integer(), nullable=True),
        sa.Column("link_status", sa.String(length=32), nullable=False),
        sa.Column("link_method", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("link_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["linked_via_match_id"],
            ["style_direction_matches.id"],
            name=op.f("fk_style_direction_style_links_linked_via_match_id_style_direction_matches"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["style_direction_id"],
            ["style_directions.id"],
            name=op.f("fk_style_direction_style_links_style_direction_id_style_directions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_direction_style_links_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_direction_style_links")),
        sa.UniqueConstraint("style_direction_id", name="uq_style_direction_style_links_style_direction_id"),
    )
    op.create_index(
        op.f("ix_style_direction_style_links_style_id"),
        "style_direction_style_links",
        ["style_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_direction_style_links_link_status"),
        "style_direction_style_links",
        ["link_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_style_direction_style_links_link_status"), table_name="style_direction_style_links")
    op.drop_index(op.f("ix_style_direction_style_links_style_id"), table_name="style_direction_style_links")
    op.drop_table("style_direction_style_links")
