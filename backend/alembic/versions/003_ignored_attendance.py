"""ignored attendance audit table

Revision ID: 003_ignored_attendance
Revises: 002_ai_insights
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_ignored_attendance"
down_revision: Union[str, Sequence[str], None] = "002_ai_insights"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ignored_attendance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_code", sa.String(length=64), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.Time(), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("work_duration_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("break_duration_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("overtime_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ignored_attendance")),
        sa.UniqueConstraint("employee_code", "work_date", name="uq_ignored_attendance_code_date"),
    )
    op.create_index(op.f("ix_ignored_attendance_employee_code"), "ignored_attendance", ["employee_code"], unique=False)
    op.create_index(op.f("ix_ignored_attendance_work_date"), "ignored_attendance", ["work_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ignored_attendance_work_date"), table_name="ignored_attendance")
    op.drop_index(op.f("ix_ignored_attendance_employee_code"), table_name="ignored_attendance")
    op.drop_table("ignored_attendance")
