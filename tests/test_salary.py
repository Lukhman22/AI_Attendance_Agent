from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config import Settings
from backend.app.database.base import Base
from backend.app.models import Attendance, Employee
from backend.app.payroll.payroll_generator import PayrollGenerator
from backend.app.payroll.salary_engine import SalaryEngine
from backend.app.utils import quantize_money
import backend.app.models  # noqa: F401
from datetime import date


def test_daily_hourly_salary():
    engine = SalaryEngine()
    daily, hourly = engine.daily_and_hourly(Decimal("52000"), 26)
    assert daily == Decimal("2000.00")
    assert hourly == Decimal("250.00")


def test_finalize_never_negative_or_above_monthly():
    engine = SalaryEngine()
    result = engine.finalize(
        monthly_salary=Decimal("1000"),
        working_days=26,
        salary_deduction=Decimal("5000"),
    )
    assert result.final_salary == Decimal("0.00")
    assert result.salary_deduction == Decimal("1000.00")

    capped = engine.finalize(
        monthly_salary=Decimal("1000"),
        working_days=26,
        salary_deduction=Decimal("-50"),
    )
    assert capped.final_salary == Decimal("1000.00")


def test_finalize_zero_deduction_int():
    """Regression: empty sum() and max(int, Decimal) must not break quantize_money."""
    engine = SalaryEngine()
    result = engine.finalize(
        monthly_salary=Decimal("52000"),
        working_days=26,
        salary_deduction=0,
    )
    assert isinstance(result.salary_deduction, Decimal)
    assert isinstance(result.final_salary, Decimal)
    assert result.salary_deduction == Decimal("0.00")
    assert result.final_salary == Decimal("52000.00")


def test_quantize_money_accepts_int_and_float():
    assert quantize_money(0) == Decimal("0.00")
    assert quantize_money(12.5) == Decimal("12.50")
    assert isinstance(quantize_money(0), Decimal)


def test_calculate_from_attendance_short_and_absent():
    engine = SalaryEngine()

    class Row:
        def __init__(self, status: str, hours: Decimal | None = None) -> None:
            self.status = status
            self.work_duration_hours = hours

    result = engine.calculate_from_attendance(
        [
            Row("present", Decimal("8.00")),
            Row("present", Decimal("7.00")),
            Row("absent", None),
            Row("weekly_off", Decimal("0")),
            Row("leave", Decimal("0")),
        ],
        monthly_salary=Decimal("30000"),
        working_days=26,
        required_hours=Decimal("8"),
    )
    # daily=1153.85, hourly=144.23 → short 1h + absent daily
    assert result.salary_deduction == Decimal("1298.08")
    assert result.final_salary == Decimal("28701.92")
    assert result.missing_hours == Decimal("9.00")


def test_payroll_skips_employees_without_attendance():
    """Payroll only includes employees present in uploaded attendance for the month."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    seeded = Employee(
        employee_code="DEMO01",
        name="Demo Only",
        department="Ops",
        monthly_salary=Decimal("99999"),
        working_days_per_month=26,
        is_active=True,
    )
    active = Employee(
        employee_code="E100",
        name="In File",
        department="Ops",
        monthly_salary=Decimal("52000"),
        working_days_per_month=26,
        is_active=True,
    )
    db.add_all([seeded, active])
    db.commit()
    db.add(
        Attendance(
            employee_id=active.id,
            work_date=date(2026, 7, 14),
            work_duration_hours=Decimal("8.00"),
            status="present",
            missing_hours=Decimal("0.00"),
            daily_deduction=Decimal("0.00"),
            source="file",
        )
    )
    db.commit()

    settings = Settings.model_construct(
        default_monthly_salary=30000.0,
        default_working_days_per_month=26,
        min_working_hours=8.0,
    )
    payroll = PayrollGenerator(db, SalaryEngine(), settings=settings).generate_month(2026, 7)
    assert len(payroll) == 1
    row = payroll[0]
    assert row.employee.employee_code == "E100"
    assert row.salary_deduction == Decimal("0.00")
    assert row.final_salary == Decimal("30000.00")
    db.close()


def test_payroll_uses_default_salary_not_seed_salary():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    employee = Employee(
        employee_code="E200",
        name="Worker",
        department="Ops",
        monthly_salary=Decimal("52000"),
        working_days_per_month=26,
        is_active=True,
    )
    db.add(employee)
    db.commit()
    db.add(
        Attendance(
            employee_id=employee.id,
            work_date=date(2026, 7, 14),
            work_duration_hours=Decimal("7.00"),
            status="present",
            missing_hours=Decimal("1.00"),
            daily_deduction=Decimal("250.00"),
            source="file",
        )
    )
    db.commit()

    settings = Settings.model_construct(
        default_monthly_salary=30000.0,
        default_working_days_per_month=26,
        min_working_hours=8.0,
    )
    payroll = PayrollGenerator(db, SalaryEngine(), settings=settings).generate_month(2026, 7)
    assert len(payroll) == 1
    # hourly from 30000 not 52000: 144.23 * 1h
    assert payroll[0].salary_deduction == Decimal("144.23")
    assert payroll[0].final_salary == Decimal("29855.77")
    db.close()
