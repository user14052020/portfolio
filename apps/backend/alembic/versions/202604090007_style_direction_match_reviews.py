"""style direction match manual review queue

Revision ID: 202604090007
Revises: 202604090006
Create Date: 2026-04-09 02:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090007"
down_revision: str | None = "202604090006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_direction_match_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("resolution_type", sa.String(length=32), nullable=True),
        sa.Column("selected_style_direction_id", sa.Integer(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["style_direction_matches.id"],
            name=op.f("fk_style_direction_match_reviews_match_id_style_direction_matches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_style_direction_id"],
            ["style_directions.id"],
            name=op.f("fk_style_direction_match_reviews_selected_style_direction_id_style_directions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_direction_match_reviews")),
        sa.UniqueConstraint("match_id", name="uq_style_direction_match_reviews_match_id"),
    )
    op.create_index(
        op.f("ix_style_direction_match_reviews_review_status"),
        "style_direction_match_reviews",
        ["review_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_style_direction_match_reviews_selected_style_direction_id"),
        "style_direction_match_reviews",
        ["selected_style_direction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_style_direction_match_reviews_selected_style_direction_id"),
        table_name="style_direction_match_reviews",
    )
    op.drop_index(op.f("ix_style_direction_match_reviews_review_status"), table_name="style_direction_match_reviews")
    op.drop_table("style_direction_match_reviews")
