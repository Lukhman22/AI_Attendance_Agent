from decimal import Decimal
from typing import Any

def resolve_salary(employee: Any) -> Decimal:
    """
    Priority 1: If an employee has an actual salary configured, always use that value.
    Priority 2: If no salary exists (or <= 0), automatically use the default demo salary of ₹35,000.
    """
    if employee is None:
        return Decimal("35000.00")
        
    salary = getattr(employee, "monthly_salary", None)
    return resolve_salary_value(salary)

def resolve_salary_value(salary: Decimal | None | int | float) -> Decimal:
    """Helper to resolve a raw salary value directly."""
    if salary is None:
        return Decimal("35000.00")
    
    val = Decimal(str(salary))
    if val <= Decimal("0"):
        return Decimal("35000.00")
        
    return val
