from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from ..config import Settings
from ..database.repositories import AttendanceRepository, EmployeeRepository, IgnoredAttendanceRepository
from ..models import Attendance, Employee
from ..payroll.salary_engine import SalaryEngine
from ..payroll.salary_resolver import resolve_salary
from ..services.employee_directory import EmployeeDirectory
from .calculator import AttendanceCalculator
from .provider import AttendanceProvider, RawAttendanceRow
from .validator import AttendanceValidator

logger = logging.getLogger(__name__)


class AttendanceTracker:
    def __init__(
        self,
        db: Session,
        calculator: AttendanceCalculator,
        validator: AttendanceValidator,
        salary_engine: SalaryEngine | None = None,
        settings: Settings | None = None,
        employee_directory: EmployeeDirectory | None = None,
    ) -> None:
        self._db = db
        self._calculator = calculator
        self._validator = validator
        self._salary_engine = salary_engine or SalaryEngine()
        self._settings = settings
        self._employees = EmployeeRepository(db)
        self._attendance = AttendanceRepository(db)
        self._ignored = IgnoredAttendanceRepository(db)
        directory_path = settings.employee_directory_file if settings else None
        self._directory = employee_directory or EmployeeDirectory(directory_path)
        self._auto_register = (
            settings.auto_register_employees_from_attendance if settings is not None else True
        )

    def ingest(self, provider: AttendanceProvider, *, source: str = "file") -> dict[str, int | list]:
        rows = provider.fetch_records()
        imported = 0
        upserted = 0
        skipped = 0
        ignored = 0
        employees_touched: set[str] = set()
        errors: list[str] = []
        ignored_records: list[dict] = []
        affected_dates: list[date] = []

        for row in rows:
            validation_errors = self._validator.validate(row)
            if validation_errors:
                skipped += 1
                errors.append(f"{row.employee_code} {row.work_date}: {'; '.join(validation_errors)}")
                continue

            employee, ignore_reason = self._resolve_employee(row)
            if employee is None:
                reason = ignore_reason or (
                    f"Employee ID {row.employee_code} does not exist in the employee database."
                )
                logger.warning(
                    "Ignoring attendance for employee %s on %s — %s",
                    row.employee_code,
                    row.work_date,
                    reason,
                )
                stored = self._ignored.upsert_unknown_employee(row, reason=reason, source=source)
                ignored += 1
                ignored_records.append(IgnoredAttendanceRepository.to_dict(stored))
                continue

            self._ignored.delete_for_employee_date(row.employee_code, row.work_date)
            employees_touched.add(employee.employee_code)

            # Attendance must ONLY track hours and status.
            # Salary deductions MUST be handled by the Payroll Generator.
            normalized = self._calculator.calculate_daily(
                row,
                hourly_salary=Decimal("0.00"),
                daily_salary=Decimal("0.00"),
            )

            existing = self._attendance.get_by_employee_and_date(employee.id, row.work_date)
            record = Attendance(
                employee_id=employee.id,
                work_date=row.work_date,
                check_in=row.check_in,
                check_out=row.check_out,
                work_duration_hours=normalized.work_duration_hours,
                break_duration_hours=normalized.break_duration_hours,
                overtime_hours=normalized.overtime_hours,
                status=normalized.status,
                missing_hours=normalized.missing_hours,
                daily_deduction=Decimal("0.00"),  # Removed duplicate logic
                source=source,
            )
            self._attendance.upsert(record)
            affected_dates.append(row.work_date)
            if existing is None:
                imported += 1
            else:
                upserted += 1

        self._db.commit()
        dates = {d for d in affected_dates}
        for item in ignored_records:
            if item.get("work_date"):
                dates.add(date.fromisoformat(item["work_date"]))

        logger.info(
            "Attendance ingest summary — employees_processed=%s attendance_records=%s "
            "imported=%s upserted=%s skipped=%s ignored=%s",
            len(employees_touched),
            imported + upserted,
            imported,
            upserted,
            skipped,
            ignored,
        )

        return {
            "imported": imported,
            "upserted": upserted,
            "skipped": skipped,
            "ignored": ignored,
            "errors": errors,
            "ignored_records": ignored_records,
            "employees_processed": len(employees_touched),
            "affected_dates": sorted(dates),
        }

    def statistics(self, start: date, end: date) -> list[dict]:
        stats = self._attendance.stats_for_range(start, end)
        results: list[dict] = []
        for employee, present, absent, leave, weekly_offs, holidays, total_hours in stats:
            worked_days = present or 0
            total_days = present + absent + leave
            percentage = Decimal("0.00")
            if total_days > 0:
                percentage = (Decimal(present) / Decimal(total_days) * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            avg = Decimal("0.00")
            if worked_days > 0:
                avg = (Decimal(str(total_hours)) / Decimal(worked_days)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            results.append(
                {
                    "employee_id": employee.id,
                    "employee_code": employee.employee_code,
                    "employee_name": employee.name,
                    "present_days": present,
                    "absent_days": absent,
                    "weekly_offs": weekly_offs,
                    "leave_days": leave,
                    "holidays": holidays,
                    "total_worked_hours": Decimal(str(total_hours)).quantize(Decimal("0.01")),
                    "average_daily_hours": avg,
                    "attendance_percentage": percentage,
                }
            )
        return results

    def _resolve_employee(self, row: RawAttendanceRow) -> tuple[Employee | None, str | None]:
        """
        Attendance export is the identity source when it includes Empcode/Name/Department.
        Salary is pulled from DB / employee directory — never invented from thin air.
        """
        code = (row.employee_code or "").strip()
        if not code:
            return None, "Employee ID is required"

        existing = self._employees.get_by_code(code)
        directory = self._directory.get(code)

        if existing is not None:
            # Refresh profile from report when present; keep salary unless directory fills a gap
            name = (row.employee_name or existing.name or code).strip()
            department = row.department if row.department is not None else existing.department
            working_days = existing.working_days_per_month
            if (not working_days or working_days <= 0) and directory and directory.working_days_per_month:
                working_days = directory.working_days_per_month
            employee = self._employees.upsert(
                employee_code=code,
                name=name,
                department=department,
                working_days_per_month=working_days or 26,
            )
            return employee, None

        if not self._auto_register:
            return None, f"Employee ID {code} does not exist in the employee database."

        # Register from attendance export identity + optional directory salary
        name = (row.employee_name or (directory.name if directory else None) or code).strip()
        department = row.department or (directory.department if directory else None)
        working_days = (
            directory.working_days_per_month
            if directory and directory.working_days_per_month
            else (self._settings.default_working_days_per_month if self._settings else 26)
        )
        logger.info(
            "Registering employee %s from attendance export (name=%s, dept=%s)",
            code,
            name,
            department,
        )
        employee = self._employees.upsert(
            employee_code=code,
            name=name,
            department=department,
            working_days_per_month=working_days,
        )
        return employee, None

    def _salary_rates(self, employee: Employee) -> tuple[Decimal, Decimal]:
        try:
            emp_salary = resolve_salary(employee, self._db)
        except ValueError:
            emp_salary = Decimal("0.00")
        return self._salary_engine.daily_and_hourly(
            emp_salary,
            employee.working_days_per_month or 26,
        )
