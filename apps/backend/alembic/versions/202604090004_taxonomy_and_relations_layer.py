"""taxonomy and relations layer

Revision ID: 202604090004
Revises: 202604090003
Create Date: 2026-04-09 19:50:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090004"
down_revision: str | None = "202604090003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_taxonomy_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("taxonomy_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_taxonomy_nodes")),
        sa.UniqueConstraint("taxonomy_type", "slug", name="uq_style_taxonomy_type_slug"),
    )
    op.create_index(
        "ix_style_taxonomy_nodes_type_slug",
        "style_taxonomy_nodes",
        ["taxonomy_type", "slug"],
        unique=False,
    )

    op.create_table(
        "style_taxonomy_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=False),
        sa.Column("taxonomy_node_id", sa.Integer(), nullable=False),
        sa.Column("link_strength", sa.Float(), nullable=False, server_default="1"),
        sa.Column("source_evidence_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_taxonomy_links_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_node_id"],
            ["style_taxonomy_nodes.id"],
            name=op.f("fk_style_taxonomy_links_taxonomy_node_id_style_taxonomy_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_id"],
            ["style_source_evidences.id"],
            name=op.f("fk_style_taxonomy_links_source_evidence_id_style_source_evidences"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_taxonomy_links")),
        sa.UniqueConstraint("style_id", "taxonomy_node_id", name="uq_style_taxonomy_link"),
    )
    op.create_index("ix_style_taxonomy_links_style_id", "style_taxonomy_links", ["style_id"], unique=False)
    op.create_index(
        "ix_style_taxonomy_links_taxonomy_node_id",
        "style_taxonomy_links",
        ["taxonomy_node_id"],
        unique=False,
    )
    op.create_index(
        "ix_style_taxonomy_links_source_evidence_id",
        "style_taxonomy_links",
        ["source_evidence_id"],
        unique=False,
    )

    op.create_table(
        "style_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_style_id", sa.Integer(), nullable=False),
        sa.Column("target_style_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_evidence_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_style_id"],
            ["styles.id"],
            name=op.f("fk_style_relations_source_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_style_id"],
            ["styles.id"],
            name=op.f("fk_style_relations_target_style_id_styles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_id"],
            ["style_source_evidences.id"],
            name=op.f("fk_style_relations_source_evidence_id_style_source_evidences"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_relations")),
        sa.UniqueConstraint(
            "source_style_id",
            "target_style_id",
            "relation_type",
            name="uq_style_relation_triplet",
        ),
    )
    op.create_index("ix_style_relations_source_style_id", "style_relations", ["source_style_id"], unique=False)
    op.create_index("ix_style_relations_target_style_id", "style_relations", ["target_style_id"], unique=False)
    op.create_index("ix_style_relations_relation_type", "style_relations", ["relation_type"], unique=False)
    op.create_index(
        "ix_style_relations_source_evidence_id",
        "style_relations",
        ["source_evidence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_style_relations_source_evidence_id", table_name="style_relations")
    op.drop_index("ix_style_relations_relation_type", table_name="style_relations")
    op.drop_index("ix_style_relations_target_style_id", table_name="style_relations")
    op.drop_index("ix_style_relations_source_style_id", table_name="style_relations")
    op.drop_table("style_relations")

    op.drop_index("ix_style_taxonomy_links_source_evidence_id", table_name="style_taxonomy_links")
    op.drop_index("ix_style_taxonomy_links_taxonomy_node_id", table_name="style_taxonomy_links")
    op.drop_index("ix_style_taxonomy_links_style_id", table_name="style_taxonomy_links")
    op.drop_table("style_taxonomy_links")

    op.drop_index("ix_style_taxonomy_nodes_type_slug", table_name="style_taxonomy_nodes")
    op.drop_table("style_taxonomy_nodes")
