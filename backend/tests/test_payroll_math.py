import pytest
from decimal import Decimal
from datetime import date
from app.models import Employee, EmployeeSalary, Attendance, Payroll
from app.payroll.payroll_generator import PayrollGenerator
from app.payroll.salary_resolver import resolve_salary
from app.ai.assistant import HRAssistant
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.config import Settings

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def test_settings():
    return Settings(
        min_working_hours=8.0,
        default_working_days_per_month=26,
    )

def test_payroll_math_validation(db_session, test_settings):
    # Setup employee
    emp = Employee(employee_code="EMP_MATH", name="Math Validation Emp")
    db_session.add(emp)
    db_session.commit()

    # Add Salary
    sal = EmployeeSalary(employee_id=emp.employee_code, monthly_salary=Decimal("55000.00"))
    db_session.add(sal)
    db_session.commit()

    # Add some attendances to create deductions
    db_session.add(Attendance(
        employee_id=emp.id,
        work_date=date(2023, 10, 1),
        status="present",
        work_duration_hours=Decimal("8"),
        source="test",
        missing_hours=Decimal("0.0"),
        daily_deduction=Decimal("0.0"),
    ))
    db_session.add(Attendance(
        employee_id=emp.id,
        work_date=date(2023, 10, 2),
        status="absent",
        work_duration_hours=Decimal("0"),
        source="test",
        missing_hours=Decimal("8.0"),
        daily_deduction=Decimal("2115.38"),
    ))
    db_session.commit()

    # Generate payroll
    generator = PayrollGenerator(db=db_session, settings=test_settings)
    payrolls = generator.generate_month(2023, 10)
    
    assert len(payrolls) == 1
    payroll = payrolls[0]
    
    # Validation 1: Base Salary - Deduction == Final Salary (with no additions)
    # Recreate the base salary that the AI will use:
    ai_calculated_base = payroll.final_salary + payroll.salary_deduction
    
    assert payroll.final_salary == ai_calculated_base - payroll.salary_deduction
    
    # Let's ensure the assistant doesn't raise a ValueError
    assistant = HRAssistant(db=db_session)
    context = {"employee_id": emp.id, "year": 2023, "month": 10, "work_date": "2023-10-01"}
    
    try:
        res = assistant.ask("why is my salary deducted?", context=context)
        assert "Base Salary" in res["answer"]
        assert "Final Salary" in res["answer"]
        assert "Total Deduction" in res["answer"]
    except ValueError as e:
        pytest.fail(f"Assistant threw ValueError for valid math: {e}")
