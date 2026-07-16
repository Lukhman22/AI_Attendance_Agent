"""ai insights schema

Revision ID: 002_ai_insights
Revises: 001_initial_schema
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_ai_insights"
down_revision: Union[str, Sequence[str], None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_daily_insight",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("employees_present", sa.Integer(), nullable=False),
        sa.Column("employees_absent", sa.Integer(), nullable=False),
        sa.Column("employees_below_min_hours", sa.Integer(), nullable=False),
        sa.Column("employees_missing_checkout", sa.Integer(), nullable=False),
        sa.Column("total_deductions", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_daily_insight")),
        sa.UniqueConstraint("work_date", name="uq_ai_daily_insight_work_date"),
    )
    op.create_index(op.f("ix_ai_daily_insight_work_date"), "ai_daily_insight", ["work_date"], unique=False)

    op.create_table(
        "ai_monthly_insight",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("company_attendance_percentage", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("average_daily_hours", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("total_salary_deductions", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_monthly_insight")),
        sa.UniqueConstraint("year", "month", name="uq_ai_monthly_insight_period"),
    )
    op.create_index(op.f("ix_ai_monthly_insight_year"), "ai_monthly_insight", ["year"], unique=False)
    op.create_index(op.f("ix_ai_monthly_insight_month"), "ai_monthly_insight", ["month"], unique=False)

    op.create_table(
        "smart_alert",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"], name=op.f("fk_smart_alert_employee_id_employee"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_smart_alert")),
    )
    op.create_index(op.f("ix_smart_alert_work_date"), "smart_alert", ["work_date"], unique=False)
    op.create_index(op.f("ix_smart_alert_employee_id"), "smart_alert", ["employee_id"], unique=False)
    op.create_index(op.f("ix_smart_alert_alert_type"), "smart_alert", ["alert_type"], unique=False)

    op.create_table(
        "ai_recommendation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"], name=op.f("fk_ai_recommendation_employee_id_employee"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_recommendation")),
    )
    op.create_index(op.f("ix_ai_recommendation_work_date"), "ai_recommendation", ["work_date"], unique=False)
    op.create_index(op.f("ix_ai_recommendation_employee_id"), "ai_recommendation", ["employee_id"], unique=False)

    op.create_table(
        "executive_summary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("estimated_deductions", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_executive_summary")),
        sa.UniqueConstraint("work_date", name="uq_executive_summary_work_date"),
    )
    op.create_index(op.f("ix_executive_summary_work_date"), "executive_summary", ["work_date"], unique=False)


def downgrade() -> None:
    op.drop_table("executive_summary")
    op.drop_table("ai_recommendation")
    op.drop_table("smart_alert")
    op.drop_table("ai_monthly_insight")
    op.drop_table("ai_daily_insight")
