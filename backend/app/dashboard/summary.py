from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..database.repositories import AttendanceRepository, IgnoredAttendanceRepository


class DailySummaryService:
    def __init__(self, db: Session) -> None:
        self._attendance = AttendanceRepository(db)
        self._ignored = IgnoredAttendanceRepository(db)

    def build(self, work_date: date, *, min_working_hours: Decimal = Decimal("8")) -> dict:
        records = self._attendance.list_for_date(work_date)
        present = [r for r in records if r.status in {"present", "missing_checkout"}]
        absent = [r for r in records if r.status == "absent"]
        below = [
            r
            for r in records
            if r.status in {"present", "missing_checkout"}
            and (r.work_duration_hours or Decimal("0")) < min_working_hours
        ]
        missing_checkout = [r for r in records if r.status == "missing_checkout" or (r.check_in and not r.check_out)]
        total_deductions = sum((r.daily_deduction or Decimal("0") for r in records), Decimal("0"))
        ignored = self._ignored.list_for_date(work_date)

        return {
            "work_date": work_date,
            "employees_present": len(present),
            "employees_absent": len(absent),
            "employees_below_min_hours": len(below),
            "employees_missing_checkout": len(missing_checkout),
            "total_deductions": total_deductions,
            "details": {
                "present": [self._brief(r) for r in present],
                "absent": [self._brief(r) for r in absent],
                "below_min_hours": [self._brief(r) for r in below],
                "missing_checkout": [self._brief(r) for r in missing_checkout],
                "ignored_records": [IgnoredAttendanceRepository.to_dict(r) for r in ignored],
            },
        }

    @staticmethod
    def _brief(record) -> dict:
        employee = record.employee
        return {
            "employee_code": employee.employee_code if employee else None,
            "employee_name": employee.name if employee else None,
            "work_duration_hours": record.work_duration_hours,
            "missing_hours": record.missing_hours,
            "daily_deduction": record.daily_deduction,
            "status": record.status,
        }
