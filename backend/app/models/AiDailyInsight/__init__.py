from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base


class AiDailyInsight(Base):
    __table_args__ = (UniqueConstraint("work_date", name="uq_ai_daily_insight_work_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    employees_present: Mapped[int] = mapped_column(Integer, default=0)
    employees_absent: Mapped[int] = mapped_column(Integer, default=0)
    employees_below_min_hours: Mapped[int] = mapped_column(Integer, default=0)
    employees_missing_checkout: Mapped[int] = mapped_column(Integer, default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
