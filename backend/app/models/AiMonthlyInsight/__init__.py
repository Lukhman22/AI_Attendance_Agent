from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, JSON, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base


class AiMonthlyInsight(Base):
    __table_args__ = (UniqueConstraint("year", "month", name="uq_ai_monthly_insight_period"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    company_attendance_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    average_daily_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"))
    total_salary_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
