from datetime import date, time
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from backend.app.attendance.calculator import AttendanceCalculator
from backend.app.attendance.csv_reader import read_attendance_file
from backend.app.attendance.provider import RawAttendanceRow
from backend.app.payroll.salary_engine import SalaryEngine


HOURLY = Decimal("250.00")
DAILY = Decimal("2000.00")


def _row(**kwargs) -> RawAttendanceRow:
    base = dict(
        employee_code="E001",
        employee_name="John Doe",
        department="Engineering",
        work_date=date(2026, 7, 14),
        check_in=time(9, 0),
        check_out=time(18, 0),
        work_duration_hours=Decimal("8.00"),
        break_duration_hours=Decimal("1.00"),
        overtime_hours=Decimal("0.00"),
        status="present",
    )
    base.update(kwargs)
    return RawAttendanceRow(**base)


@pytest.fixture
def calculator() -> AttendanceCalculator:
    return AttendanceCalculator()


def test_exactly_eight_hours(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(_row(work_duration_hours=Decimal("8.00")), hourly_salary=HOURLY, daily_salary=DAILY)
    assert result.missing_hours == Decimal("0.00")
    assert result.daily_deduction == Decimal("0.00")
    assert result.status == "present"
    assert result.payable_hours == Decimal("8.00")


def test_less_than_eight_hours(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(_row(work_duration_hours=Decimal("7.25")), hourly_salary=HOURLY, daily_salary=DAILY)
    assert result.missing_hours == Decimal("0.75")
    assert result.daily_deduction == Decimal("187.50")


def test_more_than_eight_hours_does_not_increase_pay(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(
        _row(work_duration_hours=Decimal("10.00"), overtime_hours=Decimal("2.00")),
        hourly_salary=HOURLY,
        daily_salary=DAILY,
    )
    assert result.daily_deduction == Decimal("0.00")
    assert result.payable_hours == Decimal("8.00")
    assert result.overtime_hours == Decimal("2.00")
    assert result.work_duration_hours == Decimal("10.00")


def test_absent_full_day_deduction(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(
        _row(
            check_in=None,
            check_out=None,
            work_duration_hours=None,
            break_duration_hours=None,
            overtime_hours=None,
            status="absent",
        ),
        hourly_salary=HOURLY,
        daily_salary=DAILY,
    )
    assert result.status == "absent"
    assert result.daily_deduction == DAILY
    assert result.missing_hours == Decimal("8")


def test_missing_checkout(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(
        _row(
            check_out=None,
            work_duration_hours=None,
            status="present",
        ),
        hourly_salary=HOURLY,
        daily_salary=DAILY,
    )
    assert result.status == "missing_checkout"
    assert result.work_duration_hours == Decimal("0.00")
    assert result.daily_deduction == Decimal("2000.00")


def test_work_duration_preferred_over_check_times(calculator: AttendanceCalculator):
    result = calculator.calculate_daily(
        _row(check_in=time(9, 0), check_out=time(20, 0), work_duration_hours=Decimal("7.25")),
        hourly_salary=HOURLY,
        daily_salary=DAILY,
    )
    assert result.work_duration_hours == Decimal("7.25")


def test_salary_engine_guards():
    engine = SalaryEngine()
    daily, hourly = engine.daily_and_hourly(Decimal("52000"), 26)
    assert daily == Decimal("2000.00")
    assert hourly == Decimal("250.00")
    over = engine.finalize(monthly_salary=Decimal("1000"), working_days=26, salary_deduction=Decimal("5000"))
    assert over.final_salary == Decimal("0.00")


def test_parse_csv_and_excel(tmp_path):
    csv_bytes = (
        b"Employee ID,Employee Name,Department,Date,Check-In Time,Check-Out Time,"
        b"Work Duration,Break Duration,Overtime,Attendance Status\n"
        b"E001,John Doe,Engineering,2026-07-14,09:00,17:00,7.25,1.00,0.00,Present\n"
    )
    csv_rows = read_attendance_file(BytesIO(csv_bytes), "attendance.csv")
    assert len(csv_rows) == 1
    assert csv_rows[0].work_duration_hours == Decimal("7.25")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"
    sheet.append(
        [
            "Emp ID",
            "Staff Name",
            "Dept",
            "Att Date",
            "In Time",
            "Out Time",
            "Work Hours",
            "Break Time",
            "OT Hours",
            "Day Status",
        ]
    )
    sheet.append(["E002", "Jane Smith", "HR", date(2026, 7, 14), time(9, 0), time(18, 0), time(8, 0), time(1, 0), 0.5, "Present"])
    path = tmp_path / "company_export.xlsx"
    workbook.save(path)
    excel_rows = read_attendance_file(path.open("rb"), "company_export.xlsx")
    assert len(excel_rows) == 1
    assert excel_rows[0].employee_code == "E002"
    assert excel_rows[0].work_duration_hours == Decimal("8.00")
    assert excel_rows[0].break_duration_hours == Decimal("1.00")


def test_parse_excel_with_banner_row(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Company Attendance Export", None, None, None])
    sheet.append(
        [
            "Employee ID",
            "Employee Name",
            "Department",
            "Date",
            "Check-In Time",
            "Check-Out Time",
            "Work Duration",
            "Break Duration",
            "Overtime",
            "Attendance Status",
        ]
    )
    sheet.append(["E003", "Alex Brown", "Ops", "15/07/2026", "09:00", "18:00", "8:00", "1:00", "0:30", "Present"])
    path = tmp_path / "banner_export.xlsx"
    workbook.save(path)
    rows = read_attendance_file(path.open("rb"), "banner_export.xlsx")
    assert len(rows) == 1
    assert rows[0].employee_code == "E003"
    assert rows[0].work_duration_hours == Decimal("8.00")
