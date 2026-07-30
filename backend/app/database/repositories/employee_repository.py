from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Employee


class EmployeeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self._db.get(Employee, employee_id)

    def get_by_code(self, employee_code: str) -> Employee | None:
        stmt = select(Employee).where(Employee.employee_code == employee_code)
        return self._db.scalar(stmt)

    def get_by_name(self, name: str) -> Employee | None:
        stmt = select(Employee).where(Employee.name.ilike(name))
        return self._db.scalar(stmt)

    def search_by_name(self, name: str) -> list[Employee]:
        stmt = select(Employee).where(Employee.name.ilike(f"%{name}%")).order_by(Employee.name)
        return list(self._db.scalars(stmt).all())

    def list_active(self) -> list[Employee]:
        stmt = select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.name)
        return list(self._db.scalars(stmt).all())

    def list_all(self) -> list[Employee]:
        stmt = select(Employee).order_by(Employee.name)
        return list(self._db.scalars(stmt).all())

    def upsert(
        self,
        *,
        employee_code: str,
        name: str,
        department: str | None = None,
        working_days_per_month: int | None = None,
    ) -> Employee:
        employee = self.get_by_code(employee_code)
        if employee is None:
            employee = Employee(
                employee_code=employee_code,
                name=name,
                department=department,
                working_days_per_month=working_days_per_month or 26,
            )
            self._db.add(employee)
        else:
            employee.name = name
            if department is not None:
                employee.department = department
            if working_days_per_month is not None:
                employee.working_days_per_month = working_days_per_month

        self._db.flush()
        return employee
