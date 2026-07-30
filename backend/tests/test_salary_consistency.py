import pytest
from decimal import Decimal
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

def test_salary_consistency_across_modules(db_session, test_settings):
    # Setup employee
    emp = Employee(employee_code="EMP999", name="Test Consistency")
    db_session.add(emp)
    db_session.commit()

    # Add some attendance to generate payroll
    from datetime import date
    att = Attendance(
        employee_id=emp.id,
        work_date=date(2023, 10, 1),
        status="present",
        work_duration_hours=Decimal("8"),
        source="test",
        missing_hours=Decimal("0.0"),
        daily_deduction=Decimal("0.0"),
    )
    db_session.add(att)
    db_session.commit()

    test_salaries = [23000, 30000, 45000, 80000]

    for sal_amount in test_salaries:
        # 1. Change salary
        salary_val = Decimal(str(sal_amount))
        db_session.query(EmployeeSalary).filter_by(employee_id=emp.employee_code).delete()
        sal = EmployeeSalary(employee_id=emp.employee_code, monthly_salary=salary_val)
        db_session.add(sal)
        db_session.commit()

        # 2. Generate payroll
        generator = PayrollGenerator(db=db_session, settings=test_settings)
        payrolls = generator.generate_month(2023, 10)
        assert len(payrolls) == 1
        assert payrolls[0].employee_id == emp.id

        # 3. Check Payroll Generation Matches
        # Payroll generated should have calculated deductions based on base salary
        base = resolve_salary(emp, db_session)
        assert base == salary_val
        
        # Verify the mathematical consistency constraint
        assert payrolls[0].final_salary == base - payrolls[0].salary_deduction, "Final Salary != Base Salary - Deductions"
        
        # 4. AI Answers
        ai_salary = resolve_salary(emp, db_session)
        assert ai_salary == salary_val
