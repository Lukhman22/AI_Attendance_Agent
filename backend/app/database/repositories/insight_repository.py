from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import AiDailyInsight, AiMonthlyInsight, AiRecommendation, ExecutiveSummary, SmartAlert


class InsightRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_daily(self, work_date: date) -> AiDailyInsight | None:
        return self._db.scalar(select(AiDailyInsight).where(AiDailyInsight.work_date == work_date))

    def upsert_daily(self, record: AiDailyInsight) -> AiDailyInsight:
        existing = self.get_daily(record.work_date)
        if existing is None:
            self._db.add(record)
            self._db.flush()
            return record
        existing.employees_present = record.employees_present
        existing.employees_absent = record.employees_absent
        existing.employees_below_min_hours = record.employees_below_min_hours
        existing.employees_missing_checkout = record.employees_missing_checkout
        existing.total_deductions = record.total_deductions
        existing.payload = record.payload
        self._db.flush()
        return existing

    def get_monthly(self, year: int, month: int) -> AiMonthlyInsight | None:
        return self._db.scalar(
            select(AiMonthlyInsight).where(AiMonthlyInsight.year == year, AiMonthlyInsight.month == month)
        )

    def upsert_monthly(self, record: AiMonthlyInsight) -> AiMonthlyInsight:
        existing = self.get_monthly(record.year, record.month)
        if existing is None:
            self._db.add(record)
            self._db.flush()
            return record
        existing.company_attendance_percentage = record.company_attendance_percentage
        existing.average_daily_hours = record.average_daily_hours
        existing.total_salary_deductions = record.total_salary_deductions
        existing.payload = record.payload
        self._db.flush()
        return existing

    def get_executive_summary(self, work_date: date) -> ExecutiveSummary | None:
        return self._db.scalar(select(ExecutiveSummary).where(ExecutiveSummary.work_date == work_date))

    def upsert_executive_summary(self, record: ExecutiveSummary) -> ExecutiveSummary:
        existing = self.get_executive_summary(record.work_date)
        if existing is None:
            self._db.add(record)
            self._db.flush()
            return record
        existing.summary_text = record.summary_text
        existing.estimated_deductions = record.estimated_deductions
        existing.payload = record.payload
        self._db.flush()
        return existing

    def replace_alerts_for_date(self, work_date: date, alerts: list[SmartAlert]) -> list[SmartAlert]:
        self._db.execute(delete(SmartAlert).where(SmartAlert.work_date == work_date))
        for alert in alerts:
            self._db.add(alert)
        self._db.flush()
        return alerts

    def list_alerts(
        self,
        *,
        work_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> list[SmartAlert]:
        stmt = select(SmartAlert).order_by(SmartAlert.id.desc())
        if work_date is not None:
            stmt = stmt.where(SmartAlert.work_date == work_date)
        elif year is not None and month is not None:
            from calendar import monthrange

            start = date(year, month, 1)
            end = date(year, month, monthrange(year, month)[1])
            stmt = stmt.where(SmartAlert.work_date >= start, SmartAlert.work_date <= end)
        return list(self._db.scalars(stmt).all())

    def replace_recommendations_for_date(
        self, work_date: date, recommendations: list[AiRecommendation]
    ) -> list[AiRecommendation]:
        self._db.execute(delete(AiRecommendation).where(AiRecommendation.work_date == work_date))
        for item in recommendations:
            self._db.add(item)
        self._db.flush()
        return recommendations

    def list_recommendations(self, work_date: date) -> list[AiRecommendation]:
        stmt = (
            select(AiRecommendation)
            .where(AiRecommendation.work_date == work_date)
            .order_by(AiRecommendation.id)
        )
        return list(self._db.scalars(stmt).all())
