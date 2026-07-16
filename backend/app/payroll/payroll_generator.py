from __future__ import annotations

import calendar
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..config import Settings
from ..database.repositories import AttendanceRepository, EmployeeRepository, PayrollRepository
from ..models import Payroll
from .salary_engine import SalaryEngine

logger = logging.getLogger(__name__)


class PayrollGenerator:
    def __init__(
        self,
        db: Session,
        salary_engine: SalaryEngine | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._employees = EmployeeRepository(db)
        self._attendance = AttendanceRepository(db)
        self._payroll = PayrollRepository(db)
        self._salary_engine = salary_engine or SalaryEngine()
        self._settings = settings

    def generate_month(self, year: int, month: int) -> list[Payroll]:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])

        monthly_salary = self._default_monthly_salary()
        working_days = self._default_working_days()
        required_hours = self._required_hours()

        # Only employees with uploaded attendance for this month
        month_rows = self._attendance.list_for_range(start, end)
        by_employee: dict[int, list] = {}
        for row in month_rows:
            by_employee.setdefault(row.employee_id, []).append(row)

        # Drop stale payroll (e.g. demo seed employees with no attendance this month)
        self._payroll.delete_for_period(year, month)

        results: list[Payroll] = []
        for employee_id, records in sorted(by_employee.items()):
            employee = records[0].employee or self._employees.get_by_id(employee_id)
            if employee is None:
                logger.warning("Skipping payroll for missing employee_id=%s", employee_id)
                continue

            present_days = sum(1 for r in records if r.status == "present")
            absent_days = sum(1 for r in records if r.status == "absent")
            leave_days = sum(1 for r in records if r.status == "leave")
            weekly_offs = sum(1 for r in records if r.status == "weekly_off")
            holidays = sum(1 for r in records if r.status == "holiday")
            present_days += sum(1 for r in records if r.status == "missing_checkout")

            total_hours = sum((r.work_duration_hours or Decimal("0") for r in records), Decimal("0"))
            breakdown = self._salary_engine.calculate_from_attendance(
                records,
                monthly_salary=monthly_salary,
                working_days=working_days,
                required_hours=required_hours,
            )

            payroll = Payroll(
                employee_id=employee.id,
                year=year,
                month=month,
                present_days=present_days,
                absent_days=absent_days,
                leave_days=leave_days,
                weekly_offs=weekly_offs,
                holidays=holidays,
                working_days=working_days,
                total_hours_worked=total_hours,
                missing_hours=breakdown.missing_hours,
                salary_deduction=breakdown.salary_deduction,
                final_salary=breakdown.final_salary,
                status="generated",
            )
            results.append(self._payroll.upsert(payroll))

        self._db.commit()
        logger.info(
            "Payroll generated for %s/%s — employees=%s monthly_salary=%s",
            month,
            year,
            len(results),
            monthly_salary,
        )
        return self._payroll.list_for_period(year, month)

    def list_month(self, year: int, month: int) -> list[Payroll]:
        return self._payroll.list_for_period(year, month)

    def _default_monthly_salary(self) -> Decimal:
        if self._settings is not None:
            return Decimal(str(self._settings.default_monthly_salary))
        return Decimal("30000")

    def _default_working_days(self) -> int:
        if self._settings is not None and self._settings.default_working_days_per_month > 0:
            return self._settings.default_working_days_per_month
        return 26

    def _required_hours(self) -> Decimal:
        if self._settings is not None:
            return Decimal(str(self._settings.min_working_hours))
        return Decimal("8")
