#!/usr/bin/env python3
"""Load sample employees, salary rules, and attendance for demo."""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.database.repositories import EmployeeRepository, SalaryRuleRepository
from backend.app.database.session import session_scope
from backend.app.services.csv_service import CsvService

SAMPLE_DIR = ROOT / "sample_data"


def _load_employees(session) -> None:
    repo = EmployeeRepository(session)
    path = SAMPLE_DIR / "employees.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            repo.upsert(
                employee_code=row["Employee ID"].strip(),
                name=row["Employee Name"].strip(),
                department=row.get("Department", "").strip() or None,
                monthly_salary=Decimal(row["Monthly Salary"].strip()),
                working_days_per_month=int(row["Working Days Per Month"].strip()),
            )
    print(f"Loaded employees from {path.name}")


def _seed_rules(session) -> None:
    settings = get_settings()
    SalaryRuleRepository(session).get_or_create_default(
        min_working_hours=settings.min_working_hours,
        max_payable_hours=settings.max_payable_hours,
        overtime_paid=settings.overtime_paid,
        break_duration_required=settings.break_duration_required,
    )
    print("Seeded default salary rules")


def _ingest_attendance(session, filename: str) -> None:
    settings = get_settings()
    path = SAMPLE_DIR / filename
    with path.open("rb") as handle:
        result = CsvService(session, settings).ingest_upload(handle, path.name)
    print(
        f"Ingested {filename}: imported={result.get('imported')} "
        f"upserted={result.get('upserted')} skipped={result.get('skipped')} "
        f"errors={len(result.get('errors') or [])}"
    )


def main() -> None:
    with session_scope() as session:
        _load_employees(session)
        _seed_rules(session)
        session.commit()

    with session_scope() as session:
        _ingest_attendance(session, "attendance_july.csv")
        _ingest_attendance(session, "attendance_today.csv")

    print("Demo data ready. Start the API and open the dashboard.")


if __name__ == "__main__":
    main()
