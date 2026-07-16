"""Optional local / HRMS employee directory for salary enrichment.

Attendance exports are the source of attendance identity (ID, name, department).
Salary is typically not in the biometric report — resolve it from:
  1. Employee repository (DB)
  2. Configured directory file (local CSV / future HRMS export)

Set EMPLOYEE_DIRECTORY_FILE to a CSV with columns:
  Employee ID, Employee Name, Department, Monthly Salary, Working Days Per Month
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DirectoryEmployee:
    employee_code: str
    name: str | None
    department: str | None
    monthly_salary: Decimal | None
    working_days_per_month: int | None


class EmployeeDirectory:
    """File-backed employee directory used when salary is not on the attendance row."""

    def __init__(self, path: str | Path | None) -> None:
        self._path = Path(path).expanduser() if path else None
        self._by_code: dict[str, DirectoryEmployee] = {}
        self._loaded = False

    @property
    def path(self) -> Path | None:
        return self._path

    def reload(self) -> int:
        self._by_code.clear()
        self._loaded = True
        if self._path is None:
            return 0
        if not self._path.is_file():
            logger.warning("Employee directory file not found: %s", self._path)
            return 0

        with self._path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                code = _pick(row, "Employee ID", "employee_id", "empcode", "Empcode", "code")
                if not code:
                    continue
                name = _pick(row, "Employee Name", "employee_name", "name", "Name")
                department = _pick(row, "Department", "department", "dept")
                salary_raw = _pick(row, "Monthly Salary", "monthly_salary", "salary")
                days_raw = _pick(row, "Working Days Per Month", "working_days_per_month", "working_days")
                salary = _to_decimal(salary_raw)
                days = _to_int(days_raw)
                entry = DirectoryEmployee(
                    employee_code=code.strip(),
                    name=name.strip() if name else None,
                    department=department.strip() if department else None,
                    monthly_salary=salary,
                    working_days_per_month=days,
                )
                self._by_code[entry.employee_code.casefold()] = entry

        logger.info("Loaded %s employees from directory %s", len(self._by_code), self._path)
        return len(self._by_code)

    def get(self, employee_code: str) -> DirectoryEmployee | None:
        if not self._loaded:
            self.reload()
        return self._by_code.get(employee_code.strip().casefold())


def _pick(row: dict[str, str | None], *keys: str) -> str | None:
    lowered = {str(k).strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for key in keys:
        value = lowered.get(key.lower())
        if value:
            return value
    return None


def _to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(Decimal(value.replace(",", "").strip()))
    except (InvalidOperation, ValueError):
        return None
