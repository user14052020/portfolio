"""profile and traits layer

Revision ID: 202604090003
Revises: 202604090002
Create Date: 2026-04-09 19:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090003"
down_revision: str | None = "202604090002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_source_evidences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=False),
        sa.Column("source_section_id", sa.Integer(), nullable=True),
        sa.Column("evidence_kind", sa.String(length=64), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_sources.id"],
            name=op.f("fk_style_source_evidences_source_page_id_style_sources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_section_id"],
            ["style_source_sections.id"],
            name=op.f("fk_style_source_evidences_source_section_id_style_source_sections"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_evidences")),
    )
    op.create_index(
        "ix_style_source_evidences_page_kind",
        "style_source_evidences",
        ["source_page_id", "evidence_kind"],
        unique=False,
    )
    op.create_index(
        "ix_style_source_evidences_section_id",
        "style_source_evidences",
        ["source_section_id"],
        unique=False,
    )

    op.create_table(
        "style_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("essence", sa.Text(), nullable=True),
        sa.Column("fashion_summary", sa.Text(), nullable=True),
        sa.Column("visual_summary", sa.Text(), nullable=True),
        sa.Column("historical_context", sa.Text(), nullable=True),
        sa.Column("cultural_context", sa.Text(), nullable=True),
        sa.Column("mood_keywords_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("color_palette_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("materials_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("silhouettes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("garments_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("footwear_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("accessories_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("hair_makeup_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("patterns_textures_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("seasonality_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("occasion_fit_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("negative_constraints_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("styling_advice_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("image_prompt_notes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_profiles_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_profiles")),
        sa.UniqueConstraint("style_id", name="uq_style_profiles_style_id"),
    )

    op.create_table(
        "style_traits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("trait_type", sa.String(length=64), nullable=False),
        sa.Column("trait_value", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("source_evidence_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_traits_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_id"],
            ["style_source_evidences.id"],
            name=op.f("fk_style_traits_source_evidence_id_style_source_evidences"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_traits")),
    )
    op.create_index("ix_style_traits_style_trait", "style_traits", ["style_id", "trait_type"], unique=False)
    op.create_index("ix_style_traits_trait_value", "style_traits", ["trait_value"], unique=False)
    op.create_index("ix_style_traits_source_evidence_id", "style_traits", ["source_evidence_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_style_traits_source_evidence_id", table_name="style_traits")
    op.drop_index("ix_style_traits_trait_value", table_name="style_traits")
    op.drop_index("ix_style_traits_style_trait", table_name="style_traits")
    op.drop_table("style_traits")

    op.drop_table("style_profiles")

    op.drop_index("ix_style_source_evidences_section_id", table_name="style_source_evidences")
    op.drop_index("ix_style_source_evidences_page_kind", table_name="style_source_evidences")
    op.drop_table("style_source_evidences")
