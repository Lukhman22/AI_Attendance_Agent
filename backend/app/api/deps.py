from decimal import Decimal

from fastapi import Depends
from sqlalchemy.orm import Session

from ..ai.insights_service import HRInsightsService
from ..attendance.calculator import AttendanceCalculator
from ..attendance.tracker import AttendanceTracker
from ..attendance.validator import AttendanceValidator
from ..config import Settings, get_settings
from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..database.repositories import SalaryRuleRepository
from ..database.session import get_db
from ..payroll.payroll_generator import PayrollGenerator
from ..payroll.rule_engine import RuleEngine
from ..payroll.salary_engine import SalaryEngine
from ..services.csv_service import CsvService
from ..services.notification_service import NotificationService
from ..services.report_service import ReportService


def get_app_settings() -> Settings:
    return get_settings()


def get_effective_rules(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    return RuleEngine().from_db_rule(SalaryRuleRepository(db).get_active(), settings)


def get_csv_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> CsvService:
    return CsvService(db, settings)


def get_attendance_tracker(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    rules=Depends(get_effective_rules),
) -> AttendanceTracker:
    return AttendanceTracker(
        db,
        AttendanceCalculator(
            min_working_hours=rules.min_working_hours,
            max_payable_hours=rules.max_payable_hours,
            overtime_paid=rules.overtime_paid,
        ),
        AttendanceValidator(break_duration_required=rules.break_duration_required),
        SalaryEngine(),
        settings=settings,
    )


def get_daily_summary_service(db: Session = Depends(get_db)) -> DailySummaryService:
    return DailySummaryService(db)


def get_analytics_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> AnalyticsService:
    return AnalyticsService(db, settings)


def get_payroll_generator(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> PayrollGenerator:
    return PayrollGenerator(db, SalaryEngine(), settings=settings)


def get_notification_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> NotificationService:
    return NotificationService(db, settings)


def get_report_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> ReportService:
    return ReportService(db, settings)


def get_hr_insights_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> HRInsightsService:
    return HRInsightsService(db, settings)


def get_min_working_hours(settings: Settings = Depends(get_app_settings)) -> Decimal:
    return Decimal(str(settings.min_working_hours))
