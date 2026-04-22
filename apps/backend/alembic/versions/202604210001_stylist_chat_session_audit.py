"""add stylist chat session audit metadata

Revision ID: 202604210001
Revises: 202604180001
Create Date: 2026-04-21 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202604210001"
down_revision: str | None = "202604180001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stylist_chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=True),
        sa.Column("client_ip", sa.String(length=128), nullable=True),
        sa.Column("client_user_agent", sa.Text(), nullable=True),
        sa.Column("last_active_mode", sa.String(length=64), nullable=True),
        sa.Column("last_decision_type", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stylist_chat_sessions_session_id",
        "stylist_chat_sessions",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        "ix_stylist_chat_sessions_last_message_at",
        "stylist_chat_sessions",
        ["last_message_at"],
        unique=False,
    )
    op.create_index(
        "ix_stylist_chat_sessions_client_ip",
        "stylist_chat_sessions",
        ["client_ip"],
        unique=False,
    )

    op.add_column("generation_jobs", sa.Column("client_ip", sa.String(length=128), nullable=True))
    op.add_column("generation_jobs", sa.Column("client_user_agent", sa.Text(), nullable=True))
    op.add_column("generation_jobs", sa.Column("request_origin", sa.String(length=512), nullable=True))
    op.create_index("ix_generation_jobs_client_ip", "generation_jobs", ["client_ip"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_client_ip", table_name="generation_jobs")
    op.drop_column("generation_jobs", "request_origin")
    op.drop_column("generation_jobs", "client_user_agent")
    op.drop_column("generation_jobs", "client_ip")
    op.drop_index("ix_stylist_chat_sessions_client_ip", table_name="stylist_chat_sessions")
    op.drop_index("ix_stylist_chat_sessions_last_message_at", table_name="stylist_chat_sessions")
    op.drop_index("ix_stylist_chat_sessions_session_id", table_name="stylist_chat_sessions")
    op.drop_table("stylist_chat_sessions")
