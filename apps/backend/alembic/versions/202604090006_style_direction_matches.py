"""style direction matching layer

Revision ID: 202604090006
Revises: 202604090005
Create Date: 2026-04-09 02:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090006"
down_revision: str | None = "202604090005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_direction_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("discovered_slug", sa.String(length=255), nullable=False),
        sa.Column("style_direction_id", sa.Integer(), nullable=True),
        sa.Column("match_status", sa.String(length=32), nullable=False),
        sa.Column("match_method", sa.String(length=64), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_direction_id"],
            ["style_directions.id"],
            name=op.f("fk_style_direction_matches_style_direction_id_style_directions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_direction_matches")),
        sa.UniqueConstraint("source_name", "source_url", name="uq_style_direction_match_source_url"),
    )
    op.create_index(
        op.f("ix_style_direction_matches_status"),
        "style_direction_matches",
        ["match_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_direction_matches_discovered_slug"),
        "style_direction_matches",
        ["discovered_slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_direction_matches_style_direction_id"),
        "style_direction_matches",
        ["style_direction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_style_direction_matches_style_direction_id"), table_name="style_direction_matches")
    op.drop_index(op.f("ix_style_direction_matches_discovered_slug"), table_name="style_direction_matches")
    op.drop_index(op.f("ix_style_direction_matches_status"), table_name="style_direction_matches")
    op.drop_table("style_direction_matches")
