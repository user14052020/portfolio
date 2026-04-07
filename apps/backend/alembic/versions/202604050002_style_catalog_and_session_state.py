"""style catalog and stylist session state

Revision ID: 202604050002
Revises: 202604050001
Create Date: 2026-04-05 23:35:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604050002"
down_revision: str | None = "202604050001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_directions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("source_group", sa.String(length=32), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("title_ru", sa.String(length=255), nullable=False),
        sa.Column("descriptor_en", sa.String(length=255), nullable=False),
        sa.Column("selection_weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_directions")),
        sa.UniqueConstraint("slug", name=op.f("uq_style_directions_slug")),
    )
    op.create_index(op.f("ix_style_directions_slug"), "style_directions", ["slug"], unique=True)
    op.create_index(op.f("ix_style_directions_active_sort"), "style_directions", ["is_active", "sort_order"], unique=False)
    op.create_index(op.f("ix_style_directions_source_group"), "style_directions", ["source_group"], unique=False)

    op.create_table(
        "stylist_session_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("active_intent", sa.String(length=64), nullable=True),
        sa.Column("state_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stylist_session_states")),
        sa.UniqueConstraint("session_id", name=op.f("uq_stylist_session_states_session_id")),
    )
    op.create_index(op.f("ix_stylist_session_states_session_id"), "stylist_session_states", ["session_id"], unique=True)
    op.create_index(op.f("ix_stylist_session_states_active_intent"), "stylist_session_states", ["active_intent"], unique=False)

    op.create_table(
        "stylist_style_exposures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("style_direction_id", sa.Integer(), nullable=False),
        sa.Column("shown_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_direction_id"],
            ["style_directions.id"],
            name=op.f("fk_stylist_style_exposures_style_direction_id_style_directions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stylist_style_exposures")),
        sa.UniqueConstraint(
            "session_id",
            "style_direction_id",
            "shown_on",
            name="uq_style_exposure_session_style_day",
        ),
    )
    op.create_index(op.f("ix_stylist_style_exposures_session_id"), "stylist_style_exposures", ["session_id"], unique=False)
    op.create_index(op.f("ix_stylist_style_exposures_style_direction_id"), "stylist_style_exposures", ["style_direction_id"], unique=False)
    op.create_index(op.f("ix_stylist_style_exposures_shown_on"), "stylist_style_exposures", ["shown_on"], unique=False)
    op.create_index("ix_style_exposures_session_day", "stylist_style_exposures", ["session_id", "shown_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_style_exposures_session_day", table_name="stylist_style_exposures")
    op.drop_index(op.f("ix_stylist_style_exposures_shown_on"), table_name="stylist_style_exposures")
    op.drop_index(op.f("ix_stylist_style_exposures_style_direction_id"), table_name="stylist_style_exposures")
    op.drop_index(op.f("ix_stylist_style_exposures_session_id"), table_name="stylist_style_exposures")
    op.drop_table("stylist_style_exposures")

    op.drop_index(op.f("ix_stylist_session_states_active_intent"), table_name="stylist_session_states")
    op.drop_index(op.f("ix_stylist_session_states_session_id"), table_name="stylist_session_states")
    op.drop_table("stylist_session_states")

    op.drop_index(op.f("ix_style_directions_source_group"), table_name="style_directions")
    op.drop_index(op.f("ix_style_directions_active_sort"), table_name="style_directions")
    op.drop_index(op.f("ix_style_directions_slug"), table_name="style_directions")
    op.drop_table("style_directions")
