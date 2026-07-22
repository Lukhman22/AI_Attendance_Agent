"""create_notifications_table

Revision ID: 2601fb854175
Revises: c4e5ac11246b
Create Date: 2026-07-17 14:22:50.631442
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '2601fb854175'
down_revision: str | None = 'c4e5ac11246b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
