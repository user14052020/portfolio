"""add style enrichment facet tables

Revision ID: 202604170001
Revises: 202604130001
Create Date: 2026-04-17 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604170001"
down_revision: str | None = "202604130001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_llm_enrichments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_response_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_source_pages.id"],
            name=op.f("fk_style_llm_enrichments_source_page_id_style_source_pages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_llm_enrichments_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_llm_enrichments")),
    )
    op.create_index("ix_style_llm_enrichments_style_id", "style_llm_enrichments", ["style_id"], unique=False)
    op.create_index(
        "ix_style_llm_enrichments_source_page_id",
        "style_llm_enrichments",
        ["source_page_id"],
        unique=False,
    )
    op.create_index("ix_style_llm_enrichments_status", "style_llm_enrichments", ["status"], unique=False)

    op.create_table(
        "style_knowledge_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("core_definition", sa.Text(), nullable=True),
        sa.Column("core_style_logic_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("styling_rules_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("casual_adaptations_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("statement_pieces_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("status_markers_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("overlap_context_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("historical_notes_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("negative_guidance_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_knowledge_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_knowledge_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_knowledge_facets_style_version"),
    )

    op.create_table(
        "style_visual_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("palette_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("lighting_mood_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("photo_treatment_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("visual_motifs_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("patterns_textures_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("platform_visual_cues_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_visual_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_visual_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_visual_facets_style_version"),
    )

    op.create_table(
        "style_fashion_item_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("tops_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("bottoms_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("shoes_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("accessories_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("hair_makeup_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("signature_details_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_fashion_item_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_fashion_item_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_fashion_item_facets_style_version"),
    )

    op.create_table(
        "style_image_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("hero_garments_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("secondary_garments_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("core_accessories_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("props_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("materials_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("composition_cues_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("negative_constraints_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("visual_motifs_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("lighting_mood_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("photo_treatment_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_image_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_image_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_image_facets_style_version"),
    )

    op.create_table(
        "style_relation_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("related_styles_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("overlap_styles_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("preceded_by_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("succeeded_by_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("brands_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("platforms_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("origin_regions_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("era_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_relation_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_relation_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_relation_facets_style_version"),
    )

    op.create_table(
        "style_presentation_facets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("facet_version", sa.String(length=64), nullable=False),
        sa.Column("short_explanation", sa.Text(), nullable=True),
        sa.Column("one_sentence_description", sa.Text(), nullable=True),
        sa.Column("what_makes_it_distinct_json", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_presentation_facets_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_presentation_facets")),
        sa.UniqueConstraint("style_id", "facet_version", name="uq_style_presentation_facets_style_version"),
    )


def downgrade() -> None:
    op.drop_table("style_presentation_facets")
    op.drop_table("style_relation_facets")
    op.drop_table("style_image_facets")
    op.drop_table("style_fashion_item_facets")
    op.drop_table("style_visual_facets")
    op.drop_table("style_knowledge_facets")

    op.drop_index("ix_style_llm_enrichments_status", table_name="style_llm_enrichments")
    op.drop_index("ix_style_llm_enrichments_source_page_id", table_name="style_llm_enrichments")
    op.drop_index("ix_style_llm_enrichments_style_id", table_name="style_llm_enrichments")
    op.drop_table("style_llm_enrichments")
