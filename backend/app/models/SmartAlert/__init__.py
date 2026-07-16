from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base


class SmartAlert(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL"), nullable=True, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
