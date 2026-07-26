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
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import Settings
from ..database.session import SessionLocal

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """
    Scheduling façade for HR notifications using APScheduler.
    """
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        # Generate Attendance Summary at 8 PM, Monday-Saturday (day_of_week='mon-sat')
        # We parse report_time from settings (default "20:00")
        hour, minute = self._parse_report_time(self._settings.report_time)
        
        self._scheduler.add_job(
            self._job_daily_summary,
            CronTrigger(day_of_week='mon-sat', hour=hour, minute=minute),
            id='daily_attendance_summary',
            replace_existing=True
        )
        
        logger.info(f"Scheduled Daily Attendance Summary for {hour:02d}:{minute:02d} (Mon-Sat)")

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("NotificationScheduler started.")

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("NotificationScheduler shutdown.")

    async def _job_daily_summary(self) -> None:
        logger.info("Executing scheduled job: Daily Attendance Summary")
        from ..services.notification_service import send_daily_summary
        
        db = SessionLocal()
        try:
            today_str = date.today().isoformat()
            send_daily_summary(db, target_date=today_str)
            logger.info("Daily Attendance Summary job completed successfully.")
        except Exception as e:
            logger.exception("Scheduled Daily Attendance Summary failed.")
        finally:
            db.close()

    @staticmethod
    def _parse_report_time(value: str) -> tuple[int, int]:
        try:
            parsed = datetime.strptime(value.strip(), "%H:%M")
            return parsed.hour, parsed.minute
        except ValueError:
            logger.warning("Invalid REPORT_TIME=%s, defaulting to 20:00", value)
            return 20, 0

SchedulerService = NotificationScheduler
