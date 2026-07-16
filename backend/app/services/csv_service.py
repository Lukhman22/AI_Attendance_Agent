from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from ..attendance.calculator import AttendanceCalculator
from ..attendance.provider import ApiAttendanceProvider, AttendanceProvider, FileAttendanceProvider
from ..attendance.tracker import AttendanceTracker
from ..attendance.validator import AttendanceValidator
from ..config import Settings
from ..core.exceptions import ApplicationError
from ..database.repositories import SalaryRuleRepository
from ..payroll.rule_engine import RuleEngine
from ..payroll.salary_engine import SalaryEngine

logger = logging.getLogger(__name__)
_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class CsvService:
    """Ingest attendance from CSV/Excel (or API payload) into normalized DB records."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        rules = RuleEngine().from_db_rule(SalaryRuleRepository(db).get_active(), settings)
        self._tracker = AttendanceTracker(
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

    def ingest_upload(self, file_obj: BinaryIO, filename: str) -> dict:
        safe_name = self._validate_filename(filename)
        data = file_obj.read()
        if not data:
            raise ApplicationError("Uploaded file is empty", code="attendance_file_empty")
        if len(data) > self._settings.max_upload_bytes:
            raise ApplicationError(
                f"Upload exceeds max size of {self._settings.max_upload_bytes} bytes",
                code="attendance_file_too_large",
            )

        uploads = Path(self._settings.uploads_dir)
        uploads.mkdir(parents=True, exist_ok=True)
        destination = uploads / safe_name
        destination.write_bytes(data)

        with destination.open("rb") as handle:
            provider: AttendanceProvider = FileAttendanceProvider(handle, safe_name)
            result = self._tracker.ingest(provider, source="file")

        affected_dates = result.pop("affected_dates", [])
        ingest_errors = result.get("errors") or []
        logger.info(
            "Attendance upload finished — file=%s employees_processed=%s records=%s "
            "ignored=%s skipped=%s",
            safe_name,
            result.get("employees_processed", 0),
            int(result.get("imported", 0)) + int(result.get("upserted", 0)),
            result.get("ignored", 0),
            result.get("skipped", 0),
        )
        if affected_dates:
            from ..ai.insights_service import HRInsightsService

            HRInsightsService(self._db, self._settings).run_post_ingest(
                affected_dates,
                ingest_errors=ingest_errors,
                upserted=result.get("upserted", 0),
            )
            logger.info("Post-ingest insights/notifications completed for dates=%s", affected_dates)

        return result

    def ingest_api_payload(self, payload: list[dict]) -> dict:
        """Accept biometric API payloads directly (same domain pipeline as file ingest)."""
        if not isinstance(payload, list) or not payload:
            raise ApplicationError("API payload must be a non-empty list", code="attendance_payload_invalid")
        provider = ApiAttendanceProvider(payload)
        result = self._tracker.ingest(provider, source="api")
        affected_dates = result.pop("affected_dates", [])
        ingest_errors = result.get("errors") or []
        if affected_dates:
            from ..ai.insights_service import HRInsightsService

            HRInsightsService(self._db, self._settings).run_post_ingest(
                affected_dates,
                ingest_errors=ingest_errors,
                upserted=result.get("upserted", 0),
            )
        return result

    def _validate_filename(self, filename: str | None) -> str:
        name = Path(filename or "attendance.csv").name
        name = _UNSAFE_NAME.sub("_", name).strip("._") or "attendance.csv"
        suffix = Path(name).suffix.lower()
        allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in self._settings.allowed_upload_extensions}
        if suffix not in allowed:
            raise ApplicationError(
                f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(allowed))}",
                code="attendance_file_type_invalid",
            )
        return name
