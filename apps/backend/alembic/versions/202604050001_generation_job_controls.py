"""Add generation job controls and audit fields

Revision ID: 202604050001
Revises: 202603300002
Create Date: 2026-04-05 11:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202604050001"
down_revision = "202603300002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE generation_status ADD VALUE IF NOT EXISTS 'cancelled'")
    op.add_column(
        "generation_jobs",
        sa.Column("operation_log", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("generation_jobs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_generation_jobs_deleted_at", "generation_jobs", ["deleted_at"], unique=False)
    op.alter_column("generation_jobs", "operation_log", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_deleted_at", table_name="generation_jobs")
    op.drop_column("generation_jobs", "deleted_at")
    op.drop_column("generation_jobs", "operation_log")
