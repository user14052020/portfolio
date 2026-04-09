"""canonical style layer

Revision ID: 202604090002
Revises: 202604090001
Create Date: 2026-04-09 18:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090002"
down_revision: str | None = "202604090001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "styles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("source_primary_id", sa.Integer(), nullable=True),
        sa.Column("short_definition", sa.Text(), nullable=True),
        sa.Column("long_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("first_ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_primary_id"],
            ["style_sources.id"],
            name=op.f("fk_styles_source_primary_id_style_sources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_styles")),
        sa.UniqueConstraint("slug", name=op.f("uq_styles_slug")),
    )
    op.create_index(op.f("ix_styles_slug"), "styles", ["slug"], unique=True)
    op.create_index("ix_styles_status", "styles", ["status"], unique=False)
    op.create_index("ix_styles_source_primary_id", "styles", ["source_primary_id"], unique=False)

    op.create_table(
        "style_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("alias_type", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("is_primary_match_hint", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_aliases_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_aliases")),
        sa.UniqueConstraint("style_id", "alias", "language", name="uq_style_alias_style_language"),
    )
    op.create_index("ix_style_aliases_alias_language", "style_aliases", ["alias", "language"], unique=False)
    op.create_index("ix_style_aliases_style_id", "style_aliases", ["style_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_style_aliases_style_id", table_name="style_aliases")
    op.drop_index("ix_style_aliases_alias_language", table_name="style_aliases")
    op.drop_table("style_aliases")

    op.drop_index("ix_styles_source_primary_id", table_name="styles")
    op.drop_index("ix_styles_status", table_name="styles")
    op.drop_index(op.f("ix_styles_slug"), table_name="styles")
    op.drop_table("styles")
