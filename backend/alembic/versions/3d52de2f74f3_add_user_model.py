"""Add User model

Revision ID: 3d52de2f74f3
Revises: c2525edcf56f
Create Date: 2026-07-23 13:48:41.203564
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '3d52de2f74f3'
down_revision: str | None = 'c2525edcf56f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
