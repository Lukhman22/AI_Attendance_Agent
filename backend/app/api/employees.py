from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database.repositories import EmployeeRepository, SalaryRuleRepository
from ..database.session import get_db
from ..schemas import EmployeeCreate, EmployeeRead
from .deps import get_app_settings
from ..config import Settings

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(db: Session = Depends(get_db)) -> list[EmployeeRead]:
    return [EmployeeRead.model_validate(e) for e in EmployeeRepository(db).list_all()]


@router.post("", response_model=EmployeeRead)
def create_or_update_employee(
    body: EmployeeCreate,
    db: Session = Depends(get_db),
) -> EmployeeRead:
    employee = EmployeeRepository(db).upsert(
        employee_code=body.employee_code,
        name=body.name,
        department=body.department,
        working_days_per_month=body.working_days_per_month,
    )
    db.commit()
    db.refresh(employee)
    return EmployeeRead.model_validate(employee)


@router.post("/salary-rules/seed")
def seed_salary_rules(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    rule = SalaryRuleRepository(db).get_or_create_default(
        min_working_hours=settings.min_working_hours,
        max_payable_hours=settings.max_payable_hours,
        overtime_paid=settings.overtime_paid,
        break_duration_required=settings.break_duration_required,
    )
    db.commit()
    return {
        "id": rule.id,
        "name": rule.name,
        "min_working_hours": Decimal(str(rule.min_working_hours)),
        "max_payable_hours": Decimal(str(rule.max_payable_hours)),
        "overtime_paid": rule.overtime_paid,
        "break_duration_required": rule.break_duration_required,
    }
