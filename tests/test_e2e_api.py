from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config import Settings, get_settings
from backend.app.api.deps import get_app_settings
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import create_app
from backend.app.models import Employee
import backend.app.models  # noqa: F401


@pytest.fixture()
def e2e_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    reports_dir = tmp_path / "reports"
    uploads_dir = tmp_path / "uploads"
    reports_dir.mkdir()
    uploads_dir.mkdir()

    settings = Settings.model_construct(
        app_name="AI Attendance Agent Test",
        app_version="1.0.0",
        environment="test",
        debug=True,
        api_v1_prefix="/api/v1",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        database_url=f"sqlite:///{db_path}",
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
        default_monthly_salary=30000.0,
        attendance_provider="file",
        uploads_dir=str(uploads_dir),
        reports_dir=str(reports_dir),
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
        max_upload_bytes=10 * 1024 * 1024,
        allowed_upload_extensions=[".csv", ".xlsx", ".xlsm", ".xls"],
        employee_directory_file=None,
        auto_register_employees_from_attendance=True,
    )

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app(settings)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_app_settings] = lambda: settings

    # Seed employees with salaries so deductions are meaningful
    db = TestingSessionLocal()
    db.add_all(
        [
            Employee(
                employee_code="E001",
                name="John Doe",
                department="Engineering",
                monthly_salary=Decimal("52000"),
                working_days_per_month=26,
                is_active=True,
            ),
            Employee(
                employee_code="E002",
                name="Jane Smith",
                department="HR",
                monthly_salary=Decimal("39000"),
                working_days_per_month=26,
                is_active=True,
            ),
            Employee(
                employee_code="E003",
                name="Alex Brown",
                department="Operations",
                monthly_salary=Decimal("26000"),
                working_days_per_month=26,
                is_active=True,
            ),
            Employee(
                employee_code="E004",
                name="Priya Patel",
                department="Finance",
                monthly_salary=Decimal("45000"),
                working_days_per_month=26,
                is_active=True,
            ),
            Employee(
                employee_code="E005",
                name="Michael Chen",
                department="Sales",
                monthly_salary=Decimal("34000"),
                working_days_per_month=26,
                is_active=True,
            ),
        ]
    )
    db.commit()
    db.close()

    client = TestClient(app)
    yield client, settings, reports_dir
    app.dependency_overrides.clear()


def test_health_and_home(e2e_env):
    client, _, _ = e2e_env
    assert client.get("/health").json()["status"] == "ok"
    assert "running" in client.get("/").json()["message"].lower()


def test_upload_summary_payroll_reports_ai(e2e_env):
    client, settings, reports_dir = e2e_env

    csv_content = Path("sample_data/attendance_today.csv").read_bytes()
    response = client.post(
        "/api/v1/attendance/upload",
        files={"file": ("attendance_today.csv", BytesIO(csv_content), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 5
    assert body["skipped"] == 0
    assert body.get("ignored", 0) == 0

    summary = client.get("/api/v1/attendance/daily-summary", params={"work_date": "2026-07-14"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["employees_present"] == 4
    assert payload["employees_absent"] == 1
    assert payload["employees_below_min_hours"] == 2

    records = client.get("/api/v1/attendance/records", params={"work_date": "2026-07-14"})
    assert records.status_code == 200
    assert len(records.json()) == 5

    stats = client.get(
        "/api/v1/attendance/stats",
        params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
    )
    assert stats.status_code == 200
    assert len(stats.json()) >= 1

    payroll = client.post("/api/v1/payroll/generate", json={"year": 2026, "month": 7})
    assert payroll.status_code == 200
    rows = payroll.json()
    assert len(rows) == 5
    john = next(r for r in rows if r["employee"]["name"] == "John Doe")
    assert Decimal(str(john["salary_deduction"])) == Decimal("108.17")
    assert Decimal(str(john["final_salary"])) == Decimal("29891.83")
    assert all(Decimal(str(r["final_salary"])) <= Decimal("30000") for r in rows)
    listed = client.get("/api/v1/payroll/2026/7")
    assert listed.status_code == 200
    assert len(listed.json()) == 5

    for fmt in ("csv", "excel", "pdf"):
        report = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "monthly_payroll", "format": fmt, "year": 2026, "month": 7},
        )
        assert report.status_code == 200, report.text
        path = Path(report.json()["path"])
        assert path.exists()
        assert path.stat().st_size > 0

    daily_report = client.post(
        "/api/v1/reports/generate",
        json={"report_type": "daily_summary", "format": "csv", "work_date": "2026-07-14"},
    )
    assert daily_report.status_code == 200
    report_body = daily_report.json()
    assert Path(report_body["path"]).exists()
    assert report_body["filename"]

    download = client.get(f"/api/v1/reports/download/{report_body['filename']}")
    assert download.status_code == 200
    assert download.content

    insights = client.get("/api/v1/ai/executive-summary", params={"work_date": "2026-07-14"})
    assert insights.status_code == 200
    assert "Present" in insights.json()["summary_text"]

    employees = client.get("/api/v1/employees")
    assert employees.status_code == 200
    assert len(employees.json()) == 5

    seed = client.post("/api/v1/employees/salary-rules/seed")
    assert seed.status_code == 200
    assert seed.json()["min_working_hours"] == 8.0


def test_ingest_api_and_notification_disabled(e2e_env):
    client, _, _ = e2e_env
    payload = [
        {
            "employee_id": "E001",
            "name": "John Doe",
            "department": "Engineering",
            "date": "2026-07-15",
            "check_in": "09:00",
            "check_out": "18:00",
            "work_duration": "8.00",
            "break_duration": "1.00",
            "overtime": "0",
            "status": "Present",
        }
    ]
    response = client.post("/api/v1/attendance/ingest-api", json=payload)
    assert response.status_code == 200
    assert response.json()["imported"] == 1

    notify = client.post("/api/v1/notifications/send", json={"message": "hello"})
    assert notify.status_code == 400
    assert notify.json()["error"]["code"] == "notification_provider_disabled"


def test_unknown_employee_upload_auto_registers(e2e_env):
    """Attendance export identity is registered so company HRMS codes import cleanly."""
    client, _, _ = e2e_env
    csv_content = (
        b"Employee ID,Employee Name,Department,Date,Check-In Time,Check-Out Time,"
        b"Work Duration,Break Duration,Overtime,Attendance Status\n"
        b"E001,John Doe,Engineering,2026-07-16,09:00,18:00,8.00,1.00,0.00,Present\n"
        b"1054,Ghost Worker,Ops,2026-07-16,09:00,18:00,8.00,1.00,0.00,Present\n"
    )
    response = client.post(
        "/api/v1/attendance/upload",
        files={"file": ("mixed.csv", BytesIO(csv_content), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 2
    assert body["ignored"] == 0
    assert body["employees_processed"] == 2

    employees = client.get("/api/v1/employees")
    assert employees.status_code == 200
    codes = {e["employee_code"] for e in employees.json()}
    assert "1054" in codes

    summary = client.get("/api/v1/attendance/daily-summary", params={"work_date": "2026-07-16"})
    assert summary.status_code == 200
    assert summary.json()["employees_present"] >= 1
    ignored = summary.json()["details"].get("ignored_records") or []
    assert not any(item["employee_code"] == "1054" for item in ignored)