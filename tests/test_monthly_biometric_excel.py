"""Production monthly biometric Excel layout — employee blocks with day columns."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.attendance.calculator import AttendanceCalculator
from backend.app.attendance.csv_reader import read_attendance_file
from backend.app.attendance.tracker import AttendanceTracker
from backend.app.attendance.validator import AttendanceValidator
from backend.app.database.base import Base
from backend.app.models import Employee
from backend.app.payroll.payroll_generator import PayrollGenerator
from backend.app.payroll.salary_engine import SalaryEngine
from backend.app.services.report_service import ReportService
from backend.app.config import Settings
import backend.app.models  # noqa: F401


def _build_monthly_workbook(path: Path) -> Path:
    """
    Realistic company monthly export:

    Title → employee metadata → day columns 1..N → IN/OUT/WORK/Break/OT/Status rows.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"

    sheet.append(["Company Biometric Export"])
    sheet.append(["Monthly Attendance Report - July 2026"])
    sheet.append([])

    # E001: P on 1,2,4; WO on 3; LV on 5; missing_checkout day 6 (IN only, Status P); A on 7
    # Present metadata = 4 includes the missing_checkout day
    sheet.append(
        [
            "Employee Code",
            "E001",
            "Employee Name",
            "John Doe",
            "Department",
            "Engineering",
            "Present",
            4,
            "WO",
            1,
            "HL",
            0,
            "LV",
            1,
            "Absent",
            1,
            "Total Work+OT",
            "24.50",
            "Total OT",
            "1.50",
        ]
    )
    sheet.append(["", 1, 2, 3, 4, 5, 6, 7])
    sheet.append(["IN", "09:00", "09:00", "", "09:00", "", "09:00", ""])
    sheet.append(["OUT", "18:00", "17:00", "", "19:30", "", "", ""])
    sheet.append(["WORK", "8.00", "7.00", "", "8.00", "", "", ""])
    sheet.append(["Break", "1.00", "1.00", "", "1.00", "", "0.50", ""])
    sheet.append(["OT", "0", "0", "", "1.50", "", "0", ""])
    sheet.append(["Status", "P", "P", "WO", "P", "LV", "P", "A"])

    sheet.append([])

    sheet.append(
        [
            "Employee Code",
            "E002",
            "Employee Name",
            "Jane Smith",
            "Department",
            "HR",
            "Present",
            5,
            "WO",
            1,
            "HL",
            1,
            "LV",
            0,
            "Absent",
            0,
            "Total Work+OT",
            "40.00",
            "Total OT",
            "0",
        ]
    )
    sheet.append(["", 1, 2, 3, 4, 5, 6, 7])
    sheet.append(["IN", "09:00", "09:00", "09:00", "09:00", "", "09:00", ""])
    sheet.append(["OUT", "18:00", "18:00", "18:00", "18:00", "", "18:00", ""])
    sheet.append(["WORK", "8.00", "8.00", "8.00", "8.00", "", "8.00", ""])
    sheet.append(["Break", "1.00", "1.00", "1.00", "1.00", "", "1.00", ""])
    sheet.append(["OT", "0", "0", "0", "0", "", "0", ""])
    sheet.append(["Status", "P", "P", "P", "P", "WO", "P", "HL"])

    workbook.save(path)
    return path


@pytest.fixture()
def monthly_excel(tmp_path) -> Path:
    return _build_monthly_workbook(tmp_path / "monthly_attendance_july_2026.xlsx")


def test_monthly_block_employee_detection_and_metadata(monthly_excel: Path):
    rows = read_attendance_file(monthly_excel.open("rb"), monthly_excel.name)
    codes = {r.employee_code for r in rows}
    assert codes == {"E001", "E002"}
    john = [r for r in rows if r.employee_code == "E001"]
    assert john[0].employee_name == "John Doe"
    assert john[0].department == "Engineering"


def test_monthly_block_day_normalization(monthly_excel: Path):
    rows = read_attendance_file(monthly_excel.open("rb"), monthly_excel.name)
    john = {r.work_date.day: r for r in rows if r.employee_code == "E001"}

    assert set(john) == {1, 2, 3, 4, 5, 6, 7}
    assert all(r.work_date.year == 2026 and r.work_date.month == 7 for r in john.values())

    # WORK is primary work hours
    assert john[1].work_duration_hours == Decimal("8.00")
    assert john[2].work_duration_hours == Decimal("7.00")
    assert john[4].work_duration_hours == Decimal("8.00")

    # Break stored separately
    assert john[1].break_duration_hours == Decimal("1.00")
    assert john[6].break_duration_hours == Decimal("0.50")

    # OT reporting-only field populated
    assert john[4].overtime_hours == Decimal("1.50")
    assert john[1].overtime_hours == Decimal("0.00")

    # Times
    assert john[1].check_in == time(9, 0)
    assert john[1].check_out == time(18, 0)
    assert john[6].check_in == time(9, 0)
    assert john[6].check_out is None


def test_monthly_block_status_codes(monthly_excel: Path):
    rows = read_attendance_file(monthly_excel.open("rb"), monthly_excel.name)
    calc = AttendanceCalculator()
    john = {r.work_date.day: r for r in rows if r.employee_code == "E001"}
    jane = {r.work_date.day: r for r in rows if r.employee_code == "E002"}

    assert calc.normalize_status(john[1], Decimal("8")) == "present"
    assert calc.normalize_status(john[3], Decimal("0")) == "weekly_off"
    assert calc.normalize_status(john[5], Decimal("0")) == "leave"
    assert calc.normalize_status(john[7], Decimal("0")) == "absent"
    assert calc.normalize_status(john[6], Decimal("0")) == "missing_checkout"
    assert calc.normalize_status(jane[7], Decimal("0")) == "holiday"


def test_monthly_block_totals_match_export_metadata(monthly_excel: Path):
    rows = read_attendance_file(monthly_excel.open("rb"), monthly_excel.name)
    calc = AttendanceCalculator()

    def count(code: str) -> dict[str, int]:
        tallies = {"present": 0, "absent": 0, "weekly_off": 0, "leave": 0, "holiday": 0, "missing_checkout": 0}
        for row in rows:
            if row.employee_code != code:
                continue
            hours = calc.resolve_work_hours(row)
            status = calc.normalize_status(row, hours)
            tallies[status] = tallies.get(status, 0) + 1
        return tallies

    john = count("E001")
    # Present metadata = 4 includes the missing_checkout day (still a worked attendance day in export)
    assert john["present"] + john["missing_checkout"] == 4
    assert john["weekly_off"] == 1
    assert john["leave"] == 1
    assert john["absent"] == 1

    jane = count("E002")
    assert jane["present"] == 5
    assert jane["weekly_off"] == 1
    assert jane["holiday"] == 1
    assert jane["absent"] == 0

    john_work = sum(
        (calc.resolve_work_hours(r) for r in rows if r.employee_code == "E001"),
        Decimal("0"),
    )
    john_ot = sum((r.overtime_hours or Decimal("0") for r in rows if r.employee_code == "E001"), Decimal("0"))
    assert john_work == Decimal("23.00")  # 8+7+8
    assert john_ot == Decimal("1.50")
    assert john_work + john_ot == Decimal("24.50")  # matches Total Work+OT


def test_ot_never_affects_salary_from_monthly_work(monthly_excel: Path):
    rows = read_attendance_file(monthly_excel.open("rb"), monthly_excel.name)
    calc = AttendanceCalculator()
    day4 = next(r for r in rows if r.employee_code == "E001" and r.work_date.day == 4)
    result = calc.calculate_daily(
        day4,
        hourly_salary=Decimal("250"),
        daily_salary=Decimal("2000"),
    )
    assert result.work_duration_hours == Decimal("8.00")
    assert result.overtime_hours == Decimal("1.50")
    assert result.payable_hours == Decimal("8.00")
    assert result.daily_deduction == Decimal("0.00")


def test_monthly_payroll_and_reports(monthly_excel: Path, tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    db.add_all(
        [
            Employee(
                employee_code="E001",
                name="John Doe",
                department="Engineering",
                monthly_salary=Decimal("52000"),
                working_days_per_month=26,
                is_active=True,
            ),
            Employee(
                employee_code="E002",
                name="Jane Smith",
                department="HR",
                monthly_salary=Decimal("39000"),
                working_days_per_month=26,
                is_active=True,
            ),
        ]
    )
    db.commit()

    from backend.app.attendance.provider import FileAttendanceProvider

    tracker = AttendanceTracker(
        db,
        AttendanceCalculator(),
        AttendanceValidator(break_duration_required=True),
        SalaryEngine(),
    )
    with monthly_excel.open("rb") as handle:
        result = tracker.ingest(FileAttendanceProvider(handle, monthly_excel.name), source="file")
    assert result["imported"] >= 14
    assert result["skipped"] == 0

    settings = Settings.model_construct(
        reports_dir=str(tmp_path / "reports"),
        min_working_hours=8.0,
        max_payable_hours=8.0,
        overtime_paid=False,
        break_duration_required=True,
        default_monthly_salary=30000.0,
        default_working_days_per_month=26,
    )
    payroll = PayrollGenerator(db, SalaryEngine(), settings=settings).generate_month(2026, 7)
    by_code = {p.employee.employee_code: p for p in payroll}

    john = by_code["E001"]
    # present_days includes missing_checkout
    assert john.present_days == 4
    assert john.absent_days == 1
    assert john.leave_days == 1
    assert john.weekly_offs == 1
    # Flat DEFAULT_MONTHLY_SALARY=30000: short 1h + missing_checkout(0h×8) + absent
    assert john.salary_deduction == Decimal("4250.00")
    assert john.final_salary == Decimal("47750.00")
    assert john.final_salary >= 0
    assert john.final_salary <= Decimal("52000")

    jane = by_code["E002"]
    assert jane.present_days == 5
    assert jane.weekly_offs == 1
    assert jane.holidays == 1
    assert jane.salary_deduction == Decimal("0.00")
    assert jane.final_salary == Decimal("39000.00")

    # Extra seeded employee with no July attendance must not appear
    db.add(
        Employee(
            employee_code="DEMO99",
            name="Not In File",
            department="Ops",
            monthly_salary=Decimal("99999"),
            working_days_per_month=26,
            is_active=True,
        )
    )
    db.commit()
    payroll = PayrollGenerator(db, SalaryEngine(), settings=settings).generate_month(2026, 7)
    assert {p.employee.employee_code for p in payroll} == {"E001", "E002"}

    reports = ReportService(db, settings)
    for fmt in ("csv", "excel", "pdf"):
        generated = reports.generate(report_type="monthly_payroll", fmt=fmt, year=2026, month=7)
        path = Path(generated["path"])
        assert path.exists()
        assert path.stat().st_size > 20
        if fmt == "csv":
            text = path.read_text(encoding="utf-8")
            assert "Not In File" not in text
            assert "John Doe" in text
            assert "Jane Smith" in text

    db.close()


def test_flat_csv_still_works_alongside_monthly_parser():
    csv_bytes = (
        b"Employee ID,Employee Name,Department,Date,Check-In Time,Check-Out Time,"
        b"Work Duration,Break Duration,Overtime,Attendance Status\n"
        b"E001,John Doe,Engineering,2026-07-14,09:00,17:00,7.25,1.00,0.00,Present\n"
    )
    rows = read_attendance_file(BytesIO(csv_bytes), "attendance.csv")
    assert len(rows) == 1
    assert rows[0].work_duration_hours == Decimal("7.25")
