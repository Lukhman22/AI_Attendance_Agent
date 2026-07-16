from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..utils import hours_between, quantize_money
from .provider import RawAttendanceRow


@dataclass(slots=True)
class NormalizedAttendance:
    work_duration_hours: Decimal
    break_duration_hours: Decimal | None
    overtime_hours: Decimal
    status: str
    missing_hours: Decimal
    daily_deduction: Decimal
    payable_hours: Decimal


class AttendanceCalculator:
    """Normalize biometric rows. Work Duration from device is source of truth when present."""

    def __init__(
        self,
        *,
        min_working_hours: Decimal = Decimal("8"),
        max_payable_hours: Decimal = Decimal("8"),
        overtime_paid: bool = False,
    ) -> None:
        self.min_working_hours = min_working_hours
        self.max_payable_hours = max_payable_hours
        self.overtime_paid = overtime_paid

    def resolve_work_hours(self, row: RawAttendanceRow) -> Decimal:
        if row.work_duration_hours is not None:
            return row.work_duration_hours
        calculated = hours_between(row.check_in, row.check_out)
        return calculated if calculated is not None else Decimal("0.00")

    def normalize_status(self, row: RawAttendanceRow, work_hours: Decimal) -> str:
        raw = (row.status or "").strip().lower().replace(" ", "_")
        aliases = {
            "p": "present",
            "a": "absent",
            "l": "leave",
            "lv": "leave",
            "wo": "weekly_off",
            "week_off": "weekly_off",
            "weeklyoff": "weekly_off",
            "h": "holiday",
            "hl": "holiday",
            "missing_checkout": "missing_checkout",
            "missingcheckout": "missing_checkout",
        }
        status = aliases.get(raw, raw) if raw else ""
        if status in {"absent", "leave", "weekly_off", "holiday"}:
            return status
        if status == "missing_checkout" or (row.check_in and not row.check_out):
            return "missing_checkout"
        if work_hours <= 0 and not row.check_in:
            return "absent"
        return "present"

    def calculate_daily(
        self,
        row: RawAttendanceRow,
        *,
        hourly_salary: Decimal,
        daily_salary: Decimal,
    ) -> NormalizedAttendance:
        work_hours_preview = self.resolve_work_hours(row)
        status = self.normalize_status(row, work_hours_preview)
        if status in {"absent"}:
            return NormalizedAttendance(
                work_duration_hours=Decimal("0.00"),
                break_duration_hours=row.break_duration_hours,
                overtime_hours=row.overtime_hours or Decimal("0.00"),
                status=status,
                missing_hours=self.min_working_hours,
                daily_deduction=quantize_money(daily_salary),
                payable_hours=Decimal("0.00"),
            )

        if status in {"leave", "weekly_off", "holiday"}:
            return NormalizedAttendance(
                work_duration_hours=Decimal("0.00"),
                break_duration_hours=row.break_duration_hours,
                overtime_hours=row.overtime_hours or Decimal("0.00"),
                status=status,
                missing_hours=Decimal("0.00"),
                daily_deduction=Decimal("0.00"),
                payable_hours=Decimal("0.00"),
            )

        work_hours = self.resolve_work_hours(row)
        overtime = row.overtime_hours
        if overtime is None and work_hours > self.max_payable_hours:
            overtime = work_hours - self.max_payable_hours
        overtime = overtime or Decimal("0.00")

        # Overtime is reporting-only and never increases salary.
        payable_hours = min(work_hours, self.max_payable_hours)
        if not self.overtime_paid:
            payable_hours = min(payable_hours, self.max_payable_hours)

        missing = Decimal("0.00")
        deduction = Decimal("0.00")
        if payable_hours < self.min_working_hours:
            missing = self.min_working_hours - payable_hours
            deduction = quantize_money(missing * hourly_salary)

        final_status = status
        if final_status == "present" and row.check_in and not row.check_out:
            final_status = "missing_checkout"

        return NormalizedAttendance(
            work_duration_hours=work_hours,
            break_duration_hours=row.break_duration_hours,
            overtime_hours=overtime,
            status=final_status,
            missing_hours=missing,
            daily_deduction=deduction,
            payable_hours=payable_hours,
        )
