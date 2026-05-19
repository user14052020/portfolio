"""merge site settings heads

Revision ID: ce5540d45d6b
Revises: 202605160001
Create Date: 2026-05-18 17:37:27.363347
"""

from collections.abc import Sequence


revision: str = "ce5540d45d6b"
down_revision: str = "202605160001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
