from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..attendance.tracker import AttendanceTracker
from ..attendance.calculator import AttendanceCalculator
from ..attendance.validator import AttendanceValidator
from ..config import Settings
from ..payroll.rule_engine import RuleEngine
from ..database.repositories import SalaryRuleRepository


class AnalyticsService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    def attendance_stats(self, start: date, end: date) -> list[dict]:
        rules = RuleEngine().from_db_rule(SalaryRuleRepository(self._db).get_active(), self._settings)
        tracker = AttendanceTracker(
            self._db,
            AttendanceCalculator(
                min_working_hours=rules.min_working_hours,
                max_payable_hours=rules.max_payable_hours,
                overtime_paid=rules.overtime_paid,
            ),
            AttendanceValidator(break_duration_required=rules.break_duration_required),
        )
        return tracker.statistics(start, end)
