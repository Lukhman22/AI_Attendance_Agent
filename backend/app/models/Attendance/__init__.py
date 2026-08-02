from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base


class Attendance(Base):
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    work_duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    break_duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    overtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="present")
    missing_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"))
    daily_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    leave_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="file")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee", back_populates="attendance_records")
