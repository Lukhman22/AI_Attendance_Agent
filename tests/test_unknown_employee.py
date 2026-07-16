from decimal import Decimal
from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.attendance.calculator import AttendanceCalculator
from backend.app.attendance.provider import FileAttendanceProvider
from backend.app.attendance.tracker import AttendanceTracker
from backend.app.attendance.validator import AttendanceValidator
from backend.app.config import Settings
from backend.app.database.base import Base
from backend.app.models import Attendance, Employee, IgnoredAttendance
from backend.app.payroll.payroll_generator import PayrollGenerator
from backend.app.payroll.salary_engine import SalaryEngine
from backend.app.services.employee_directory import EmployeeDirectory
import backend.app.models  # noqa: F401


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return Session()


def _settings(**overrides) -> Settings:
    base = dict(
        employee_directory_file=None,
        auto_register_employees_from_attendance=True,
        default_working_days_per_month=26,
        min_working_hours=8.0,
        max_payable_hours=8.0,
        overtime_paid=False,
        break_duration_required=True,
    )
    base.update(overrides)
    return Settings.model_construct(**base)


def test_report_employee_is_registered_from_attendance_export(tmp_path):
    """Attendance export is the identity source — register Empcode/Name/Dept from the file."""
    db = _session()
    directory_csv = tmp_path / "directory.csv"
    directory_csv.write_text(
        "Employee ID,Employee Name,Department,Monthly Salary,Working Days Per Month\n"
        "1054,Unknown Worker,Ops,30000,26\n",
        encoding="utf-8",
    )
    csv_bytes = (
        b"Employee ID,Employee Name,Department,Date,Check-In Time,Check-Out Time,"
        b"Work Duration,Break Duration,Overtime,Attendance Status\n"
        b"1054,Unknown Worker,Ops,2026-07-14,09:00,18:00,8.00,1.00,0.00,Present\n"
    )
    tracker = AttendanceTracker(
        db,
        AttendanceCalculator(),
        AttendanceValidator(break_duration_required=True),
        SalaryEngine(),
        settings=_settings(
            employee_directory_file=str(directory_csv),
            auto_register_employees_from_attendance=True,
        ),
        employee_directory=EmployeeDirectory(directory_csv),
    )
    result = tracker.ingest(FileAttendanceProvider(BytesIO(csv_bytes), "attendance.csv"))

    assert result["imported"] == 1
    assert result["ignored"] == 0
    assert result["employees_processed"] == 1

    employee = db.scalar(select(Employee).where(Employee.employee_code == "1054"))
    assert employee is not None
    assert employee.name == "Unknown Worker"
    assert employee.department == "Ops"
    assert employee.monthly_salary == Decimal("30000")

    attendance = list(db.scalars(select(Attendance)).all())
    assert len(attendance) == 1

    payroll = PayrollGenerator(db, SalaryEngine()).generate_month(2026, 7)
    assert len(payroll) == 1
    assert payroll[0].employee.employee_code == "1054"
    db.close()


def test_strict_mode_ignores_unknown_employee_when_auto_register_disabled():
    db = _session()
    db.add(
        Employee(
            employee_code="E001",
            name="John Doe",
            department="Engineering",
            monthly_salary=Decimal("52000"),
            working_days_per_month=26,
            is_active=True,
        )
    )
    db.commit()

    csv_bytes = (
        b"Employee ID,Employee Name,Department,Date,Check-In Time,Check-Out Time,"
        b"Work Duration,Break Duration,Overtime,Attendance Status\n"
        b"E001,John Doe,Engineering,2026-07-14,09:00,18:00,8.00,1.00,0.00,Present\n"
        b"1054,Unknown Worker,Ops,2026-07-14,09:00,18:00,8.00,1.00,0.00,Present\n"
    )
    tracker = AttendanceTracker(
        db,
        AttendanceCalculator(),
        AttendanceValidator(break_duration_required=True),
        SalaryEngine(),
        settings=_settings(auto_register_employees_from_attendance=False, employee_directory_file=None),
        employee_directory=EmployeeDirectory(None),
    )
    result = tracker.ingest(FileAttendanceProvider(BytesIO(csv_bytes), "attendance.csv"))

    assert result["imported"] == 1
    assert result["ignored"] == 1
    assert result["ignored_records"][0]["employee_code"] == "1054"
    assert {e.employee_code for e in db.scalars(select(Employee)).all()} == {"E001"}
    assert len(list(db.scalars(select(IgnoredAttendance)).all())) == 1
    db.close()


def test_production_xls_registers_company_employees_with_directory_salary():
    path = Path("sample_data/monthperformance_june_2026.xls")
    if not path.exists():
        return
    db = _session()
    tracker = AttendanceTracker(
        db,
        AttendanceCalculator(),
        AttendanceValidator(break_duration_required=True),
        SalaryEngine(),
        settings=_settings(employee_directory_file="sample_data/employees.csv"),
        employee_directory=EmployeeDirectory("sample_data/employees.csv"),
    )
    result = tracker.ingest(FileAttendanceProvider(path.open("rb"), path.name))
    assert result["ignored"] == 0
    assert result["employees_processed"] >= 5
    assert result["imported"] + result["upserted"] >= 100

    azeem = db.scalar(select(Employee).where(Employee.employee_code == "K6k031"))
    assert azeem is not None
    assert azeem.name == "Azeem"
    assert azeem.monthly_salary == Decimal("55000")

    payroll = PayrollGenerator(db, SalaryEngine()).generate_month(2026, 6)
    codes = {p.employee.employee_code for p in payroll}
    assert "K6k031" in codes
    db.close()
