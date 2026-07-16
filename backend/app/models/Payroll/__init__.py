from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base


class Payroll(Base):
    __table_args__ = (UniqueConstraint("employee_id", "year", "month", name="uq_payroll_employee_period"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    present_days: Mapped[int] = mapped_column(Integer, default=0)
    absent_days: Mapped[int] = mapped_column(Integer, default=0)
    leave_days: Mapped[int] = mapped_column(Integer, default=0)
    weekly_offs: Mapped[int] = mapped_column(Integer, default=0)
    holidays: Mapped[int] = mapped_column(Integer, default=0)
    working_days: Mapped[int] = mapped_column(Integer, default=0)
    total_hours_worked: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    missing_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    salary_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    final_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(32), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee", back_populates="payroll_records")
