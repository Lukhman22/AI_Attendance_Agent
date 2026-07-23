"""Add attendance annotations table

Revision ID: 84864ca83ede
Revises: 2601fb854175
Create Date: 2026-07-23 11:09:21.756688
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '84864ca83ede'
down_revision: str | None = '2601fb854175'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
