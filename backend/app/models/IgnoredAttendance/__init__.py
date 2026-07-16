from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base


class IgnoredAttendance(Base):
    """Audit log for attendance rows skipped because the employee is not registered."""

    __table_args__ = (
        UniqueConstraint("employee_code", "work_date", name="uq_ignored_attendance_code_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(64), index=True)
    employee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    work_duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    break_duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    overtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="file")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
