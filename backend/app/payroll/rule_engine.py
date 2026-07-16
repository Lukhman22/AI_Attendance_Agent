from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..config import Settings


@dataclass(slots=True)
class EffectiveRules:
    min_working_hours: Decimal
    max_payable_hours: Decimal
    overtime_paid: bool
    break_duration_required: bool


class RuleEngine:
    def from_settings(self, settings: Settings) -> EffectiveRules:
        return EffectiveRules(
            min_working_hours=Decimal(str(settings.min_working_hours)),
            max_payable_hours=Decimal(str(settings.max_payable_hours)),
            overtime_paid=settings.overtime_paid,
            break_duration_required=settings.break_duration_required,
        )

    def from_db_rule(self, rule, settings: Settings) -> EffectiveRules:
        if rule is None:
            return self.from_settings(settings)
        return EffectiveRules(
            min_working_hours=Decimal(str(rule.min_working_hours)),
            max_payable_hours=Decimal(str(rule.max_payable_hours)),
            overtime_paid=bool(rule.overtime_paid),
            break_duration_required=bool(rule.break_duration_required),
        )
