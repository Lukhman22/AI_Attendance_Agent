from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AiDailyInsight, AiMonthlyInsight, ExecutiveSummary
from ..database.repositories import InsightRepository, PayrollRepository
from ..services.notification_service import NotificationService
from .analyzer import HRAnalyzer
from .prompts import EXECUTIVE_SUMMARY_POLISH_PROMPT

logger = logging.getLogger(__name__)


class HRInsightsService:
    """Orchestrates deterministic analysis, persistence, optional LLM polish, and notifications."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._repo = InsightRepository(db)
        self._analyzer = HRAnalyzer(db, settings)

    def run_post_ingest(
        self,
        work_dates: list[date],
        *,
        ingest_errors: list[str] | None = None,
        upserted: int = 0,
    ) -> None:
        unique_dates = sorted(set(work_dates))
        for work_date in unique_dates:
            self.analyze_and_store_daily(
                work_date, ingest_errors=ingest_errors, ingest_upserted=upserted
            )

        if unique_dates:
            latest = unique_dates[-1]
            self.analyze_and_store_monthly(latest.year, latest.month)

        self._db.commit()

        if unique_dates and self._settings.ai_auto_notify:
            self._send_executive_notification(unique_dates[-1])

    def analyze_and_store_daily(
        self,
        work_date: date,
        *,
        ingest_errors: list[str] | None = None,
        ingest_upserted: int = 0,
    ) -> dict:
        result = self._analyzer.analyze_daily(
            work_date, ingest_errors=ingest_errors, ingest_upserted=ingest_upserted
        )
        daily = result["daily_insight"]
        insight = self._repo.upsert_daily(
            AiDailyInsight(
                work_date=daily["work_date"],
                employees_present=daily["employees_present"],
                employees_absent=daily["employees_absent"],
                employees_below_min_hours=daily["employees_below_min_hours"],
                employees_missing_checkout=daily["employees_missing_checkout"],
                total_deductions=daily["total_deductions"],
                payload=daily["payload"],
            )
        )
        self._repo.replace_alerts_for_date(work_date, result["alerts"])
        self._repo.replace_recommendations_for_date(work_date, result["recommendations"])

        exec_data = result["executive_summary"]
        summary_text = exec_data["summary_text"]
        if self._settings.openai_api_key:
            summary_text = self._polish_executive_summary(summary_text) or summary_text

        executive = self._repo.upsert_executive_summary(
            ExecutiveSummary(
                work_date=exec_data["work_date"],
                summary_text=summary_text,
                estimated_deductions=exec_data["estimated_deductions"],
                payload=exec_data["payload"],
            )
        )
        self._db.flush()
        return {
            "daily_insight": insight,
            "executive_summary": executive,
            "alerts": result["alerts"],
            "recommendations": result["recommendations"],
        }

    def analyze_and_store_monthly(self, year: int, month: int) -> AiMonthlyInsight:
        result = self._analyzer.analyze_monthly(year, month)
        record = self._repo.upsert_monthly(
            AiMonthlyInsight(
                year=result["year"],
                month=result["month"],
                company_attendance_percentage=result["company_attendance_percentage"],
                average_daily_hours=result["average_daily_hours"],
                total_salary_deductions=result["total_salary_deductions"],
                payload=result["payload"],
            )
        )
        self._db.flush()
        return record

    def get_daily_insight(self, work_date: date, *, generate: bool = True) -> AiDailyInsight | None:
        existing = self._repo.get_daily(work_date)
        if existing or not generate:
            return existing
        self.analyze_and_store_daily(work_date)
        self._db.commit()
        return self._repo.get_daily(work_date)

    def get_monthly_insight(self, year: int, month: int, *, generate: bool = True) -> AiMonthlyInsight | None:
        existing = self._repo.get_monthly(year, month)
        if existing or not generate:
            return existing
        self.analyze_and_store_monthly(year, month)
        self._db.commit()
        return self._repo.get_monthly(year, month)

    def get_executive_summary(self, work_date: date, *, generate: bool = True) -> ExecutiveSummary | None:
        existing = self._repo.get_executive_summary(work_date)
        if existing or not generate:
            return existing
        self.analyze_and_store_daily(work_date)
        self._db.commit()
        return self._repo.get_executive_summary(work_date)

    def get_alerts(
        self,
        *,
        work_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ):
        return self._repo.list_alerts(work_date=work_date, year=year, month=month)

    def get_recommendations(self, work_date: date) -> list:
        return self._repo.list_recommendations(work_date)

    def _send_executive_notification(self, work_date: date) -> None:
        if self._settings.notification_provider == "none":
            logger.info("Skipping auto notification; provider is none")
            return
        from ..services.notification_service import generate_daily_executive_report
        msg = generate_daily_executive_report(self._db, work_date)
        try:
            NotificationService(self._db, self._settings).send(msg)
            self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Auto executive summary notification failed")
            self._db.rollback()

    def send_monthly_payroll_notification(self, year: int, month: int) -> None:
        if self._settings.notification_provider == "none":
            logger.info("Skipping monthly payroll notification; provider is none")
            return
        from ..services.notification_service import generate_monthly_payroll_report
        msg = generate_monthly_payroll_report(self._db, month, year)
        try:
            NotificationService(self._db, self._settings).send(msg)
            self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Monthly payroll notification failed")
            self._db.rollback()

    def _polish_executive_summary(self, text: str) -> str | None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._settings.openai_api_key)
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {"role": "system", "content": EXECUTIVE_SUMMARY_POLISH_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Improve readability only. Do not change numbers, names, or recommendations.\n\n"
                            f"{text}"
                        ),
                    },
                ],
                temperature=0,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception:  # noqa: BLE001
            logger.exception("Executive summary polish failed")
            return None
