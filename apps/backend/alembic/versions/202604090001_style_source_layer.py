"""style source layer

Revision ID: 202604090001
Revises: 202604050002
Create Date: 2026-04-09 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090001"
down_revision: str | None = "202604050002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_site", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source_hash", sa.Text(), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_sections_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("normalizer_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_sources")),
    )
    op.create_index("ix_style_sources_site_url", "style_sources", ["source_site", "source_url"], unique=False)
    op.create_index("ix_style_sources_source_hash", "style_sources", ["source_hash"], unique=False)
    op.create_index("ix_style_sources_last_seen_at", "style_sources", ["last_seen_at"], unique=False)

    op.create_table(
        "style_source_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("section_level", sa.Integer(), nullable=True),
        sa.Column("section_text", sa.Text(), nullable=False),
        sa.Column("section_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_sources.id"],
            name=op.f("fk_style_source_sections_source_page_id_style_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_sections")),
    )
    op.create_index(
        "ix_style_source_sections_source_page_order",
        "style_source_sections",
        ["source_page_id", "section_order"],
        unique=False,
    )
    op.create_index("ix_style_source_sections_section_hash", "style_source_sections", ["section_hash"], unique=False)

    op.create_table(
        "style_source_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=False),
        sa.Column("anchor_text", sa.Text(), nullable=True),
        sa.Column("target_title", sa.Text(), nullable=True),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_sources.id"],
            name=op.f("fk_style_source_links_source_page_id_style_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_links")),
    )
    op.create_index("ix_style_source_links_page_type", "style_source_links", ["source_page_id", "link_type"], unique=False)

    op.create_table(
        "style_source_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("license_if_available", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_page_id"],
            ["style_sources.id"],
            name=op.f("fk_style_source_images_source_page_id_style_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_source_images")),
    )
    op.create_index(
        "ix_style_source_images_page_position",
        "style_source_images",
        ["source_page_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_style_source_images_page_position", table_name="style_source_images")
    op.drop_table("style_source_images")

    op.drop_index("ix_style_source_links_page_type", table_name="style_source_links")
    op.drop_table("style_source_links")

    op.drop_index("ix_style_source_sections_section_hash", table_name="style_source_sections")
    op.drop_index("ix_style_source_sections_source_page_order", table_name="style_source_sections")
    op.drop_table("style_source_sections")

    op.drop_index("ix_style_sources_last_seen_at", table_name="style_sources")
    op.drop_index("ix_style_sources_source_hash", table_name="style_sources")
    op.drop_index("ix_style_sources_site_url", table_name="style_sources")
    op.drop_table("style_sources")
