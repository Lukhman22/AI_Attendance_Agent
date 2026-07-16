from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.ai.analyzer import HRAnalyzer
from backend.app.ai.insights_service import HRInsightsService
from backend.app.attendance.calculator import AttendanceCalculator
from backend.app.attendance.provider import RawAttendanceRow
from backend.app.attendance.tracker import AttendanceTracker
from backend.app.attendance.validator import AttendanceValidator
from backend.app.config import Settings
from backend.app.database.base import Base
from backend.app.models import Employee
import backend.app.models  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = Session()
    session.add(
        Employee(
            employee_code="E001",
            name="Ahmed",
            department="Ops",
            monthly_salary=Decimal("26000"),
            working_days_per_month=26,
            is_active=True,
        )
    )
    session.add(
        Employee(
            employee_code="E002",
            name="Sarah",
            department="HR",
            monthly_salary=Decimal("39000"),
            working_days_per_month=26,
            is_active=True,
        )
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def settings() -> Settings:
    return Settings.model_construct(
        app_name="test",
        app_version="1",
        environment="test",
        debug=True,
        api_v1_prefix="/api/v1",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        database_url="sqlite://",
        postgres_server="localhost",
        postgres_port=5432,
        postgres_user="postgres",
        postgres_password="postgres",
        postgres_db="test",
        db_echo=False,
        db_pool_size=5,
        db_max_overflow=0,
        db_pool_timeout=30,
        db_pool_recycle=1800,
        log_level="WARNING",
        log_format="plain",
        backend_cors_origins=["*"],
        trusted_hosts=["*"],
        min_working_hours=8.0,
        max_payable_hours=8.0,
        overtime_paid=False,
        break_duration_required=True,
        default_working_days_per_month=26,
        attendance_provider="file",
        uploads_dir="uploads",
        reports_dir="reports",
        notification_provider="none",
        telegram_token=None,
        telegram_chat_id=None,
        whatsapp_token=None,
        whatsapp_group_id=None,
        whatsapp_phone_number_id=None,
        whatsapp_template_name=None,
        whatsapp_template_language="en_US",
        whatsapp_api_version="v19.0",
        report_time="18:30",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        max_upload_bytes=10_000_000,
        allowed_upload_extensions=[".csv"],
        late_arrival_time="09:30",
        short_workday_threshold_hours=8.0,
        extremely_short_workday_hours=2.0,
        ai_auto_notify=False,
    )


def _ingest_row(session, settings, row: RawAttendanceRow):
    tracker = AttendanceTracker(
        session,
        AttendanceCalculator(min_working_hours=Decimal("8")),
        AttendanceValidator(break_duration_required=True),
    )
    from backend.app.attendance.provider import ApiAttendanceProvider

    provider = ApiAttendanceProvider(
        [
            {
                "employee_code": row.employee_code,
                "employee_name": row.employee_name,
                "department": row.department,
                "work_date": row.work_date.isoformat(),
                "check_in": row.check_in.isoformat() if row.check_in else None,
                "check_out": row.check_out.isoformat() if row.check_out else None,
                "work_duration": str(row.work_duration_hours) if row.work_duration_hours is not None else None,
                "break_duration": str(row.break_duration_hours) if row.break_duration_hours is not None else None,
                "overtime": "0",
                "status": row.status,
            }
        ]
    )
    result = tracker.ingest(provider)
    session.commit()
    return result


def test_daily_analysis_detects_short_hours_and_missing_checkout(db_session, settings):
    work_date = date(2026, 7, 14)
    _ingest_row(
        db_session,
        settings,
        RawAttendanceRow(
            employee_code="E001",
            employee_name="Ahmed",
            department="Ops",
            work_date=work_date,
            check_in=time(9, 0),
            check_out=time(17, 0),
            work_duration_hours=Decimal("7.25"),
            break_duration_hours=Decimal("1"),
            overtime_hours=Decimal("0"),
            status="present",
        ),
    )
    _ingest_row(
        db_session,
        settings,
        RawAttendanceRow(
            employee_code="E002",
            employee_name="Sarah",
            department="HR",
            work_date=work_date,
            check_in=time(9, 0),
            check_out=None,
            work_duration_hours=None,
            break_duration_hours=Decimal("1"),
            overtime_hours=None,
            status="present",
        ),
    )

    service = HRInsightsService(db_session, settings)
    result = service.analyze_and_store_daily(work_date)
    db_session.commit()

    insight = result["daily_insight"]
    assert insight.employees_present == 2
    assert insight.employees_below_min_hours == 2
    assert insight.employees_missing_checkout == 1
    assert len(result["alerts"]) >= 2
    assert any(r.confidence in {"high", "medium", "low"} for r in result["recommendations"])
    assert all("HR should" not in r.recommendation for r in result["recommendations"])
    assert "Present" in result["executive_summary"].summary_text
    assert "Key Findings" in result["executive_summary"].summary_text


def test_recommendation_includes_evidence(db_session, settings):
    work_date = date(2026, 7, 15)
    for offset in range(4):
        day = work_date - timedelta(days=offset)
        _ingest_row(
            db_session,
            settings,
            RawAttendanceRow(
                employee_code="E001",
                employee_name="Ahmed",
                department="Ops",
                work_date=day,
                check_in=time(9, 0),
                check_out=time(16, 0),
                work_duration_hours=Decimal("6.5"),
                break_duration_hours=Decimal("1"),
                overtime_hours=Decimal("0"),
                status="present",
            ),
        )

    analyzer = HRAnalyzer(db_session, settings)
    analysis = analyzer.analyze_daily(work_date)
    repeated = analysis["daily_insight"]["payload"]["repeated_short_workdays"]
    assert repeated
    assert repeated[0]["employee_name"] == "Ahmed"
    assert analysis["recommendations"]
    assert analysis["recommendations"][0].evidence.get("attendance_records")


def test_monthly_insight_includes_all_employees(db_session, settings):
    work_date = date(2026, 7, 10)
    _ingest_row(
        db_session,
        settings,
        RawAttendanceRow(
            employee_code="E001",
            employee_name="Ahmed",
            department="Ops",
            work_date=work_date,
            check_in=time(9, 0),
            check_out=time(18, 0),
            work_duration_hours=Decimal("8"),
            break_duration_hours=Decimal("1"),
            overtime_hours=Decimal("0"),
            status="present",
        ),
    )
    service = HRInsightsService(db_session, settings)
    monthly = service.analyze_and_store_monthly(2026, 7)
    db_session.commit()
    assert len(monthly.payload["employees"]) >= 1
    assert "payroll_summary" in monthly.payload
