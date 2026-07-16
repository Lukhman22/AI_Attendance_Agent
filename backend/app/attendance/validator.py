from __future__ import annotations

from decimal import Decimal

from ..core.exceptions import ApplicationError
from .provider import RawAttendanceRow


class AttendanceValidator:
    def __init__(self, *, break_duration_required: bool = True) -> None:
        self._break_duration_required = break_duration_required

    def validate(self, row: RawAttendanceRow) -> list[str]:
        errors: list[str] = []
        if not row.employee_code:
            errors.append("Employee ID is required")
        if not row.employee_name:
            errors.append("Employee Name is required")
        if row.work_date is None:
            errors.append("Date is required")

        status = (row.status or "").strip().lower().replace(" ", "_")
        if status in {
            "absent",
            "a",
            "leave",
            "l",
            "lv",
            "weekly_off",
            "week_off",
            "wo",
            "holiday",
            "h",
            "hl",
            "missing_checkout",
            "missingcheckout",
        }:
            return errors

        if self._break_duration_required and row.break_duration_hours is None:
            errors.append("Break duration must be recorded")

        if row.work_duration_hours is None and row.check_in is None and row.check_out is None:
            errors.append("Work duration or check-in/check-out are required")
        elif row.work_duration_hours is None and row.check_in is not None and row.check_out is None:
            # Missing checkout is allowed and tracked separately.
            return errors
        elif row.work_duration_hours is None and (row.check_in is None or row.check_out is None):
            errors.append("Work duration or both check-in and check-out are required")

        if row.work_duration_hours is not None and row.work_duration_hours < Decimal("0"):
            errors.append("Work duration cannot be negative")

        return errors

    def ensure_valid(self, row: RawAttendanceRow) -> None:
        errors = self.validate(row)
        if errors:
            raise ApplicationError(
                "Attendance row validation failed",
                code="attendance_validation_error",
                details={"employee_code": row.employee_code, "errors": errors},
            )
