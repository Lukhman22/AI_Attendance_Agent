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
from .salary_resolver import resolve_salary

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

        working_days = self._default_working_days()
        required_hours = self._required_hours()

        # Pull all active employees so Payroll matches HR Reports exactly
        active_employees = self._employees.list_active()

        # Group attendance by employee
        month_rows = self._attendance.list_for_range(start, end)
        by_employee: dict[int, list] = {}
        for row in month_rows:
            by_employee.setdefault(row.employee_id, []).append(row)

        # Drop existing payroll for this period before regenerating
        self._payroll.delete_for_period(year, month)

        from sqlalchemy import select, func
        from ..models import EmployeeSalary
        from ..core.exceptions import ApplicationError

        missing_salaries = []
        emp_salary_map = {}

        # 1. Validate all active employees have salaries
        for employee in active_employees:
            stmt = select(EmployeeSalary).where(func.lower(EmployeeSalary.employee_id) == func.lower(employee.employee_code))
            salary_record = self._db.scalars(stmt).first()
            
            if not salary_record or salary_record.monthly_salary <= 0:
                missing_salaries.append(f"{employee.employee_code} ({employee.name})")
            else:
                emp_salary_map[employee.id] = salary_record.monthly_salary

        if missing_salaries:
            logger.error("Missing salaries for: %s", missing_salaries)
            raise ApplicationError(
                "Cannot generate payroll. Some employees are missing salary configurations.",
                code="missing_salary",
                details=missing_salaries
            )

        results: list[Payroll] = []
        # 2. Generate payroll for EVERY active employee
        for employee in active_employees:
            records = by_employee.get(employee.id, [])

            present_days = sum(1 for r in records if r.status == "present")
            absent_days = sum(1 for r in records if r.status == "absent")
            leave_days = sum(1 for r in records if r.status == "leave")
            weekly_offs = sum(1 for r in records if r.status == "weekly_off")
            holidays = sum(1 for r in records if r.status == "holiday")
            present_days += sum(1 for r in records if r.status == "missing_checkout")

            total_hours = sum((r.work_duration_hours or Decimal("0") for r in records), Decimal("0"))
            
            emp_salary = emp_salary_map[employee.id]
            
            breakdown = self._salary_engine.calculate_from_attendance(
                records,
                monthly_salary=emp_salary,
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
            "Payroll generated for %s/%s — employees=%s",
            month,
            year,
            len(results),
        )
        return self._payroll.list_for_period(year, month)

    def list_month(self, year: int, month: int) -> list[Payroll]:
        return self._payroll.list_for_period(year, month)


    def _default_working_days(self) -> int:
        if self._settings is not None and self._settings.default_working_days_per_month > 0:
            return self._settings.default_working_days_per_month
        return 26

    def _required_hours(self) -> Decimal:
        if self._settings is not None:
            return Decimal(str(self._settings.min_working_hours))
        return Decimal("8")
