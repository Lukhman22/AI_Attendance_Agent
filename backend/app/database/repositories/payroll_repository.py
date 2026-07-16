from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...models import Payroll


class PayrollRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_employee_period(self, employee_id: int, year: int, month: int) -> Payroll | None:
        stmt = select(Payroll).where(
            Payroll.employee_id == employee_id,
            Payroll.year == year,
            Payroll.month == month,
        )
        return self._db.scalar(stmt)

    def list_for_period(self, year: int, month: int) -> list[Payroll]:
        stmt = (
            select(Payroll)
            .options(joinedload(Payroll.employee))
            .where(Payroll.year == year, Payroll.month == month)
            .order_by(Payroll.id)
        )
        return list(self._db.scalars(stmt).unique().all())

    def delete_for_period(self, year: int, month: int) -> int:
        existing = self.list_for_period(year, month)
        for row in existing:
            self._db.delete(row)
        self._db.flush()
        return len(existing)

    def upsert(self, record: Payroll) -> Payroll:
        existing = self.get_for_employee_period(record.employee_id, record.year, record.month)
        if existing is None:
            self._db.add(record)
            self._db.flush()
            return record

        for field in (
            "present_days",
            "absent_days",
            "leave_days",
            "weekly_offs",
            "holidays",
            "working_days",
            "total_hours_worked",
            "missing_hours",
            "salary_deduction",
            "final_salary",
            "status",
        ):
            setattr(existing, field, getattr(record, field))
        self._db.flush()
        return existing
