"""Add telegram_bot_token

Revision ID: 6f6cfe14dfed
Revises: 3d52de2f74f3
Create Date: 2026-07-24 10:30:49.995012
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '6f6cfe14dfed'
down_revision: str | None = '3d52de2f74f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
