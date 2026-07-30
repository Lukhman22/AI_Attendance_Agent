from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base

class EmployeeSalary(Base):
    __tablename__ = "employee_salary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    employee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
