from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ..utils import _money_decimal, quantize_money


@dataclass(slots=True)
class SalaryBreakdown:
    daily_salary: Decimal
    hourly_salary: Decimal
    missing_hours: Decimal
    salary_deduction: Decimal
    final_salary: Decimal


class SalaryEngine:
    """Flat monthly salary rules: OT never paid; deduct from uploaded attendance only."""

    def daily_and_hourly(self, monthly_salary: Decimal, working_days: int) -> tuple[Decimal, Decimal]:
        monthly = _money_decimal(monthly_salary)
        days = working_days if working_days > 0 else 26
        daily = quantize_money(monthly / Decimal(days))
        hourly = quantize_money(daily / Decimal("8"))
        return daily, hourly

    def deduction_for_missing_hours(self, missing_hours: Decimal, hourly_salary: Decimal) -> Decimal:
        missing = _money_decimal(missing_hours)
        if missing <= 0:
            return Decimal("0.00")
        return quantize_money(missing * _money_decimal(hourly_salary))

    def calculate_from_attendance(
        self,
        records: list[Any],
        *,
        monthly_salary: Decimal,
        working_days: int,
        required_hours: Decimal = Decimal("8"),
    ) -> SalaryBreakdown:
        """
        Deduct only from actual uploaded attendance rows for the month.

        - work hours >= required → no deduction
        - work hours < required → (required - worked) × hourly rate
        - absent → daily salary
        - leave / weekly_off / holiday → no deduction
        """
        monthly = _money_decimal(monthly_salary)
        required = _money_decimal(required_hours)
        daily, hourly = self.daily_and_hourly(monthly, working_days)

        deduction = Decimal("0.00")
        missing_total = Decimal("0.00")

        for record in records:
            status = (getattr(record, "status", None) or "").strip().lower()
            if status in {"leave", "weekly_off", "holiday"}:
                continue

            if status == "absent":
                deduction += daily
                missing_total += required
                continue

            worked = _money_decimal(getattr(record, "work_duration_hours", None) or Decimal("0"))
            if worked >= required:
                continue

            missing = required - worked
            missing_total += missing
            deduction += missing * hourly

        if deduction > monthly:
            deduction = monthly
        if deduction < 0:
            deduction = Decimal("0.00")

        final = monthly - deduction
        if final < 0:
            final = Decimal("0.00")
        if final > monthly:
            final = monthly

        return SalaryBreakdown(
            daily_salary=daily,
            hourly_salary=hourly,
            missing_hours=missing_total.quantize(Decimal("0.01")),
            salary_deduction=quantize_money(deduction),
            final_salary=quantize_money(final),
        )

    def finalize(
        self,
        *,
        monthly_salary: Decimal,
        working_days: int,
        salary_deduction: Decimal,
    ) -> SalaryBreakdown:
        monthly = _money_decimal(monthly_salary)
        daily, hourly = self.daily_and_hourly(monthly, working_days)
        deduction = max(_money_decimal(salary_deduction), Decimal("0.00"))
        if deduction > monthly:
            deduction = monthly
        final = monthly - deduction
        if final < 0:
            final = Decimal("0.00")
        if final > monthly:
            final = monthly
        return SalaryBreakdown(
            daily_salary=daily,
            hourly_salary=hourly,
            missing_hours=Decimal("0.00"),
            salary_deduction=quantize_money(deduction),
            final_salary=quantize_money(final),
        )
