from pathlib import Path

from backend.app.config import Settings
from backend.app.services.report_service import ReportService
from backend.app.dashboard.summary import DailySummaryService
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.base import Base
from backend.app.models import Attendance, Employee
import backend.app.models  # noqa: F401


def test_report_formats_write_non_empty_files(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reports.db'}")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    employee = Employee(
        employee_code="E001",
        name="John Doe",
        department="Engineering",
        monthly_salary=Decimal("52000"),
        working_days_per_month=26,
        is_active=True,
    )
    db.add(employee)
    db.flush()
    db.add(
        Attendance(
            employee_id=employee.id,
            work_date=date(2026, 7, 14),
            status="present",
            work_duration_hours=Decimal("8.00"),
            break_duration_hours=Decimal("1.00"),
            overtime_hours=Decimal("0.00"),
            missing_hours=Decimal("0.00"),
            daily_deduction=Decimal("0.00"),
            source="file",
        )
    )
    db.commit()

    settings = Settings.model_construct(
        reports_dir=str(tmp_path / "out"),
        min_working_hours=8.0,
        max_payable_hours=8.0,
        overtime_paid=False,
        break_duration_required=True,
    )
    service = ReportService(db, settings)
    for fmt in ("csv", "excel", "pdf"):
        result = service.generate(report_type="daily_summary", fmt=fmt, work_date=date(2026, 7, 14))
        path = Path(result["path"])
        assert path.exists()
        assert path.stat().st_size > 20
        assert result["filename"] == path.name
        resolved = service.resolve_download_path(result["filename"])
        assert resolved == path.resolve()
    db.close()
