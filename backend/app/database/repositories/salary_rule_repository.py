from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import SalaryRule


class SalaryRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self) -> SalaryRule | None:
        stmt = select(SalaryRule).where(SalaryRule.is_active.is_(True)).order_by(SalaryRule.id).limit(1)
        return self._db.scalar(stmt)

    def get_or_create_default(
        self,
        *,
        min_working_hours: float,
        max_payable_hours: float,
        overtime_paid: bool,
        break_duration_required: bool,
    ) -> SalaryRule:
        existing = self.get_active()
        if existing is not None:
            return existing

        rule = SalaryRule(
            name="default",
            min_working_hours=min_working_hours,
            max_payable_hours=max_payable_hours,
            overtime_paid=overtime_paid,
            break_duration_required=break_duration_required,
            is_active=True,
        )
        self._db.add(rule)
        self._db.flush()
        return rule
