from __future__ import annotations

"""
Notification scheduling abstraction.

Current behaviour (event-driven — do not change without an explicit product decision):
  • Attendance upload  → daily executive summary notification
  • Payroll generation → monthly payroll summary notification

This module intentionally does NOT run APScheduler, Celery, or cron.
Future operators may plug a real scheduler behind NotificationScheduler /
SchedulerService while reusing NotificationService.send(...).
"""

import logging
from datetime import datetime, time
from typing import Protocol

from ..config import Settings

logger = logging.getLogger(__name__)


class SchedulerBackend(Protocol):
    """Future plug-in surface for APScheduler, Celery beat, system cron, etc."""

    def schedule_daily_report(self, hour: int, minute: int) -> None: ...

    def schedule_monthly_payroll_report(self, day_of_month: int, hour: int, minute: int) -> None: ...


class NotificationScheduler:
    """
    Lightweight scheduling façade for HR notifications.

    Production today: event-driven only (upload / payroll generate triggers).
    Future: assign a SchedulerBackend implementation; do not rewrite NotificationService.
    """

    def __init__(self, settings: Settings, backend: SchedulerBackend | None = None) -> None:
        self._settings = settings
        self._backend = backend

    @property
    def mode(self) -> str:
        return "external_backend" if self._backend is not None else "event_driven"

    def should_run_now(self, now: datetime | None = None) -> bool:
        """Helper for an external cron/worker that polls REPORT_TIME."""
        now = now or datetime.now()
        hour, minute = self._parse_report_time(self._settings.report_time)
        return now.hour == hour and now.minute == minute

    def prepare_future_schedule(self) -> dict[str, str]:
        """Document intended jobs without registering them."""
        hour, minute = self._parse_report_time(self._settings.report_time)
        return {
            "mode": self.mode,
            "daily_attendance_summary": f"{hour:02d}:{minute:02d} (event-driven today; REPORT_TIME hint)",
            "monthly_payroll_summary": "on payroll generate (event-driven today)",
            "note": (
                "Wire APScheduler/Celery/cron via SchedulerBackend when needed. "
                "Keep NotificationService as the send path."
            ),
        }

    def attach_backend(self, backend: SchedulerBackend) -> None:
        """Optional future hook — does not start any jobs by itself."""
        self._backend = backend
        logger.info("NotificationScheduler backend attached: %s", type(backend).__name__)

    @staticmethod
    def _parse_report_time(value: str) -> tuple[int, int]:
        try:
            parsed = time.fromisoformat(value.strip())
            return parsed.hour, parsed.minute
        except ValueError:
            logger.warning("Invalid REPORT_TIME=%s, defaulting to 18:30", value)
            return 18, 30


# Alias preferred in docs / dependency injection discussions
SchedulerService = NotificationScheduler
