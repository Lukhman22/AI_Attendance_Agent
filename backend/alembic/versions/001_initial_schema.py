"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column("monthly_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("working_days_per_month", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee")),
        sa.UniqueConstraint("employee_code", name=op.f("uq_employee_employee_code")),
    )
    op.create_index(op.f("ix_employee_employee_code"), "employee", ["employee_code"], unique=False)
    op.create_index(op.f("ix_employee_name"), "employee", ["name"], unique=False)

    op.create_table(
        "salary_rule",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("min_working_hours", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("max_payable_hours", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("overtime_paid", sa.Boolean(), nullable=False),
        sa.Column("break_duration_required", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_salary_rule")),
        sa.UniqueConstraint("name", name=op.f("uq_salary_rule_name")),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_log")),
    )
    op.create_index(op.f("ix_notification_log_provider"), "notification_log", ["provider"], unique=False)

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.Time(), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("work_duration_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("break_duration_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("overtime_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("missing_hours", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("daily_deduction", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"], name=op.f("fk_attendance_employee_id_employee"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attendance")),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),
    )
    op.create_index(op.f("ix_attendance_employee_id"), "attendance", ["employee_id"], unique=False)
    op.create_index(op.f("ix_attendance_work_date"), "attendance", ["work_date"], unique=False)
    op.create_index(op.f("ix_attendance_status"), "attendance", ["status"], unique=False)

    op.create_table(
        "payroll",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("present_days", sa.Integer(), nullable=False),
        sa.Column("absent_days", sa.Integer(), nullable=False),
        sa.Column("leave_days", sa.Integer(), nullable=False),
        sa.Column("weekly_offs", sa.Integer(), nullable=False),
        sa.Column("holidays", sa.Integer(), nullable=False),
        sa.Column("working_days", sa.Integer(), nullable=False),
        sa.Column("total_hours_worked", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("missing_hours", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("salary_deduction", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("final_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"], name=op.f("fk_payroll_employee_id_employee"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payroll")),
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_payroll_employee_period"),
    )
    op.create_index(op.f("ix_payroll_employee_id"), "payroll", ["employee_id"], unique=False)
    op.create_index(op.f("ix_payroll_year"), "payroll", ["year"], unique=False)
    op.create_index(op.f("ix_payroll_month"), "payroll", ["month"], unique=False)


def downgrade() -> None:
    op.drop_table("payroll")
    op.drop_table("attendance")
    op.drop_table("notification_log")
    op.drop_table("salary_rule")
    op.drop_table("employee")
