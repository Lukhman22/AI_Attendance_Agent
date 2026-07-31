from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from ...models import AiDailyInsight, AiMonthlyInsight, AiRecommendation, ExecutiveSummary, SmartAlert


class InsightRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_daily(self, work_date: date) -> AiDailyInsight | None:
        return self._db.scalar(select(AiDailyInsight).where(AiDailyInsight.work_date == work_date))

    def upsert_daily(self, record: AiDailyInsight) -> AiDailyInsight:
        stmt = insert(AiDailyInsight).values(
            work_date=record.work_date,
            employees_present=record.employees_present,
            employees_absent=record.employees_absent,
            employees_below_min_hours=record.employees_below_min_hours,
            employees_missing_checkout=record.employees_missing_checkout,
            total_deductions=record.total_deductions,
            payload=record.payload
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['work_date'],
            set_={
                'employees_present': stmt.excluded.employees_present,
                'employees_absent': stmt.excluded.employees_absent,
                'employees_below_min_hours': stmt.excluded.employees_below_min_hours,
                'employees_missing_checkout': stmt.excluded.employees_missing_checkout,
                'total_deductions': stmt.excluded.total_deductions,
                'payload': stmt.excluded.payload,
            }
        )
        self._db.execute(stmt)
        self._db.flush()
        return self.get_daily(record.work_date)

    def get_monthly(self, year: int, month: int) -> AiMonthlyInsight | None:
        return self._db.scalar(
            select(AiMonthlyInsight).where(AiMonthlyInsight.year == year, AiMonthlyInsight.month == month)
        )

    def upsert_monthly(self, record: AiMonthlyInsight) -> AiMonthlyInsight:
        stmt = insert(AiMonthlyInsight).values(
            year=record.year,
            month=record.month,
            company_attendance_percentage=record.company_attendance_percentage,
            average_daily_hours=record.average_daily_hours,
            total_salary_deductions=record.total_salary_deductions,
            payload=record.payload
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['year', 'month'],
            set_={
                'company_attendance_percentage': stmt.excluded.company_attendance_percentage,
                'average_daily_hours': stmt.excluded.average_daily_hours,
                'total_salary_deductions': stmt.excluded.total_salary_deductions,
                'payload': stmt.excluded.payload,
            }
        )
        self._db.execute(stmt)
        self._db.flush()
        return self.get_monthly(record.year, record.month)

    def get_executive_summary(self, work_date: date) -> ExecutiveSummary | None:
        return self._db.scalar(select(ExecutiveSummary).where(ExecutiveSummary.work_date == work_date))

    def upsert_executive_summary(self, record: ExecutiveSummary) -> ExecutiveSummary:
        stmt = insert(ExecutiveSummary).values(
            work_date=record.work_date,
            summary_text=record.summary_text,
            estimated_deductions=record.estimated_deductions,
            payload=record.payload
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['work_date'],
            set_={
                'summary_text': stmt.excluded.summary_text,
                'estimated_deductions': stmt.excluded.estimated_deductions,
                'payload': stmt.excluded.payload,
            }
        )
        self._db.execute(stmt)
        self._db.flush()
        return self.get_executive_summary(record.work_date)

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
