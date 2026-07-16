from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base


class SalaryRule(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, default="default")
    min_working_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("8.00"))
    max_payable_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("8.00"))
    overtime_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    break_duration_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
