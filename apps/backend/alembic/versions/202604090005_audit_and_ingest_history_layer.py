"""audit and ingest history layer

Revision ID: 202604090005
Revises: 202604090004
Create Date: 2026-04-09 20:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604090005"
down_revision: str | None = "202604090004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_ingest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("styles_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("styles_matched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("styles_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("styles_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("styles_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parser_version", sa.Text(), nullable=True),
        sa.Column("normalizer_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_ingest_runs")),
    )
    op.create_index("ix_style_ingest_runs_started_at", "style_ingest_runs", ["started_at"], unique=False)
    op.create_index("ix_style_ingest_runs_source_name", "style_ingest_runs", ["source_name"], unique=False)

    op.create_table(
        "style_ingest_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("style_id", sa.Integer(), nullable=True),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=True),
        sa.Column("old_value_hash", sa.Text(), nullable=True),
        sa.Column("new_value_hash", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["style_ingest_runs.id"],
            name=op.f("fk_style_ingest_changes_run_id_style_ingest_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["style_id"],
            ["styles.id"],
            name=op.f("fk_style_ingest_changes_style_id_styles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_ingest_changes")),
    )
    op.create_index("ix_style_ingest_changes_run_id", "style_ingest_changes", ["run_id"], unique=False)
    op.create_index("ix_style_ingest_changes_style_id", "style_ingest_changes", ["style_id"], unique=False)
    op.create_index("ix_style_ingest_changes_change_type", "style_ingest_changes", ["change_type"], unique=False)
    op.create_index("ix_style_ingest_changes_field_name", "style_ingest_changes", ["field_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_style_ingest_changes_field_name", table_name="style_ingest_changes")
    op.drop_index("ix_style_ingest_changes_change_type", table_name="style_ingest_changes")
    op.drop_index("ix_style_ingest_changes_style_id", table_name="style_ingest_changes")
    op.drop_index("ix_style_ingest_changes_run_id", table_name="style_ingest_changes")
    op.drop_table("style_ingest_changes")

    op.drop_index("ix_style_ingest_runs_source_name", table_name="style_ingest_runs")
    op.drop_index("ix_style_ingest_runs_started_at", table_name="style_ingest_runs")
    op.drop_table("style_ingest_runs")
