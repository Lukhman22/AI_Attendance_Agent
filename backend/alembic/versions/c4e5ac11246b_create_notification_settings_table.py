"""Create notification_settings table

Revision ID: c4e5ac11246b
Revises: 003_ignored_attendance
Create Date: 2026-07-17 14:16:34.156035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c4e5ac11246b'
down_revision: str | None = '003_ignored_attendance'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("telegram_chat_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_settings")),
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
