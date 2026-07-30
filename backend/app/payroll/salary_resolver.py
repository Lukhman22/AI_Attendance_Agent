from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import EmployeeSalary

def resolve_salary(employee: Any, db: Session) -> Decimal:
    """
    Returns the configured salary for an employee from the EmployeeSalary table.
    If missing, raises ValueError.
    """
    if employee is None:
        raise ValueError("Salary has not been configured for this employee.")
        
    stmt = select(EmployeeSalary).where(EmployeeSalary.employee_id == employee.employee_code)
    salary_record = db.scalars(stmt).first()
    
    if not salary_record or salary_record.monthly_salary <= Decimal("0"):
        raise ValueError("Salary has not been configured for this employee.")
        
    return resolve_salary_value(salary_record.monthly_salary)

def resolve_salary_value(salary: Decimal | None | int | float) -> Decimal:
    """Helper to resolve a raw salary value directly."""
    if salary is None:
        return Decimal("0.00")
    
    val = Decimal(str(salary))
    if val <= Decimal("0"):
        return Decimal("0.00")
        
    return val
