from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from ..config import Settings
from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..database.repositories import (
    AttendanceRepository,
    EmployeeRepository,
    IgnoredAttendanceRepository,
    PayrollRepository,
    SalaryRuleRepository,
)
from ..models import AiRecommendation, SmartAlert
from ..payroll.rule_engine import RuleEngine


@dataclass(slots=True)
class AnalysisContext:
    min_working_hours: Decimal
    late_arrival_time: time
    short_workday_threshold: Decimal
    extremely_short_threshold: Decimal


def _record_evidence(record) -> dict:
    employee = record.employee
    return {
        "attendance_id": record.id,
        "employee_id": record.employee_id,
        "employee_code": employee.employee_code if employee else None,
        "employee_name": employee.name if employee else None,
        "work_date": record.work_date.isoformat(),
        "check_in": record.check_in.isoformat() if record.check_in else None,
        "check_out": record.check_out.isoformat() if record.check_out else None,
        "work_duration_hours": float(record.work_duration_hours or 0),
        "missing_hours": float(record.missing_hours or 0),
        "daily_deduction": float(record.daily_deduction or 0),
        "status": record.status,
    }


class HRAnalyzer:
    """Deterministic HR analysis — no LLM, no duplicated payroll math."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        rules = RuleEngine().from_db_rule(SalaryRuleRepository(db).get_active(), settings)
        self._ctx = AnalysisContext(
            min_working_hours=rules.min_working_hours,
            late_arrival_time=time.fromisoformat(settings.late_arrival_time),
            short_workday_threshold=Decimal(str(settings.short_workday_threshold_hours)),
            extremely_short_threshold=Decimal(str(settings.extremely_short_workday_hours)),
        )
        self._attendance = AttendanceRepository(db)
        self._employees = EmployeeRepository(db)
        self._payroll = PayrollRepository(db)
        self._ignored = IgnoredAttendanceRepository(db)

    def analyze_daily(
        self,
        work_date: date,
        *,
        ingest_errors: list[str] | None = None,
        ingest_upserted: int = 0,
    ) -> dict:
        summary = DailySummaryService(self._db).build(work_date, min_working_hours=self._ctx.min_working_hours)
        records = self._attendance.list_for_date(work_date)

        below_hours = [
            _record_evidence(r)
            for r in records
            if r.status in {"present", "missing_checkout"}
            and (r.work_duration_hours or Decimal("0")) < self._ctx.min_working_hours
        ]
        missing_checkout = [
            _record_evidence(r)
            for r in records
            if r.status == "missing_checkout" or (r.check_in and not r.check_out)
        ]
        absent = [_record_evidence(r) for r in records if r.status == "absent"]
        late_arrivals = [
            _record_evidence(r)
            for r in records
            if r.check_in and r.check_in > self._ctx.late_arrival_time and r.status != "absent"
        ]
        extremely_short = [
            _record_evidence(r)
            for r in records
            if r.work_duration_hours is not None
            and r.work_duration_hours < self._ctx.extremely_short_threshold
            and r.status in {"present", "missing_checkout"}
        ]

        repeated_short = self._repeated_short_workdays(work_date)
        consecutive_absences = self._consecutive_absences(work_date)

        alerts = self._build_alerts(
            work_date,
            records,
            ingest_errors=ingest_errors or [],
            ingest_upserted=ingest_upserted,
            below_hours=below_hours,
            missing_checkout=missing_checkout,
            absent=absent,
            extremely_short=extremely_short,
            consecutive_absences=consecutive_absences,
        )
        recommendations = self._build_recommendations(
            work_date,
            below_hours=below_hours,
            missing_checkout=missing_checkout,
            absent=absent,
            repeated_short=repeated_short,
            consecutive_absences=consecutive_absences,
        )

        attention_names = sorted(
            {
                *(row["employee_name"] for row in below_hours if row.get("employee_name")),
                *(row["employee_name"] for row in missing_checkout if row.get("employee_name")),
                *(row["employee_name"] for row in absent if row.get("employee_name")),
                *(item["employee_name"] for item in repeated_short),
                *(item["employee_name"] for item in consecutive_absences),
            }
        )

        ignored_records = summary.get("details", {}).get("ignored_records") or []
        payload = {
            "work_date": work_date.isoformat(),
            "below_min_hours": below_hours,
            "missing_checkout": missing_checkout,
            "absent": absent,
            "late_arrivals": late_arrivals,
            "repeated_short_workdays": repeated_short,
            "consecutive_absences": consecutive_absences,
            "extremely_short_workdays": extremely_short,
            "employees_requiring_attention": attention_names,
            "ignored_records": ignored_records,
            "alerts_count": len(alerts),
            "recommendations_count": len(recommendations),
        }

        return {
            "daily_insight": {
                "work_date": work_date,
                "employees_present": summary["employees_present"],
                "employees_absent": summary["employees_absent"],
                "employees_below_min_hours": summary["employees_below_min_hours"],
                "employees_missing_checkout": summary["employees_missing_checkout"],
                "total_deductions": summary["total_deductions"],
                "payload": payload,
            },
            "alerts": alerts,
            "recommendations": recommendations,
            "executive_summary": self._build_executive_summary(
                work_date,
                summary=summary,
                attention_names=attention_names,
                recommendations=recommendations,
                ignored_records=ignored_records,
            ),
        }

    def analyze_monthly(self, year: int, month: int) -> dict:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        stats = AnalyticsService(self._db, self._settings).attendance_stats(start, end)
        payroll_rows = self._payroll.list_for_period(year, month)

        employee_rows = []
        frequent_below = []
        repeated_absent = []
        total_deductions = Decimal("0.00")
        total_hours = Decimal("0.00")
        total_leaves = 0

        for row in stats:
            total_hours += Decimal(str(row["total_worked_hours"]))
            total_leaves += row["leave_days"]
            employee_rows.append(
                {
                    "employee_id": row["employee_id"],
                    "employee_code": row["employee_code"],
                    "employee_name": row["employee_name"],
                    "attendance_percentage": float(row["attendance_percentage"]),
                    "total_worked_hours": float(row["total_worked_hours"]),
                    "average_daily_hours": float(row["average_daily_hours"]),
                    "present_days": row["present_days"],
                    "absent_days": row["absent_days"],
                    "leave_days": row["leave_days"],
                }
            )
            if row["absent_days"] >= 2:
                repeated_absent.append(
                    {
                        "employee_id": row["employee_id"],
                        "employee_name": row["employee_name"],
                        "absent_days": row["absent_days"],
                    }
                )

        for emp in self._employees.list_active():
            records = self._attendance.list_for_employee_range(emp.id, start, end)
            below_count = sum(
                1
                for r in records
                if r.status in {"present", "missing_checkout"}
                and (r.work_duration_hours or Decimal("0")) < self._ctx.min_working_hours
            )
            if below_count >= 2:
                frequent_below.append(
                    {
                        "employee_id": emp.id,
                        "employee_name": emp.name,
                        "days_below_min_hours": below_count,
                    }
                )

        payroll_summary = []
        for p in payroll_rows:
            total_deductions += p.salary_deduction or Decimal("0")
            payroll_summary.append(
                {
                    "employee_id": p.employee_id,
                    "employee_name": p.employee.name if p.employee else None,
                    "present_days": p.present_days,
                    "absent_days": p.absent_days,
                    "leave_days": p.leave_days,
                    "missing_hours": float(p.missing_hours or 0),
                    "salary_deduction": float(p.salary_deduction or 0),
                    "final_salary": float(p.final_salary or 0),
                }
            )

        company_present = sum(r["present_days"] for r in employee_rows)
        company_absent = sum(r["absent_days"] for r in employee_rows)
        company_leave = sum(r["leave_days"] for r in employee_rows)
        company_total = company_present + company_absent + company_leave
        company_pct = Decimal("0.00")
        if company_total > 0:
            company_pct = (Decimal(company_present) / Decimal(company_total) * Decimal("100")).quantize(
                Decimal("0.01")
            )
        avg_daily = Decimal("0.00")
        if stats:
            avg_daily = (
                sum(Decimal(str(s["average_daily_hours"])) for s in stats) / Decimal(len(stats))
            ).quantize(Decimal("0.01"))

        payload = {
            "year": year,
            "month": month,
            "employees": employee_rows,
            "frequent_below_min_hours": frequent_below,
            "repeated_absences": repeated_absent,
            "payroll_summary": payroll_summary,
            "overall_company_attendance_percentage": float(company_pct),
            "average_daily_working_hours": float(avg_daily),
            "total_working_hours": float(total_hours),
            "total_leaves": total_leaves,
            "total_salary_deductions": float(total_deductions),
        }

        return {
            "year": year,
            "month": month,
            "company_attendance_percentage": company_pct,
            "average_daily_hours": avg_daily,
            "total_salary_deductions": total_deductions,
            "payload": payload,
        }

    def _repeated_short_workdays(self, work_date: date, lookback_days: int = 7) -> list[dict]:
        start = work_date - timedelta(days=lookback_days - 1)
        results: list[dict] = []
        for emp in self._employees.list_active():
            records = self._attendance.list_for_employee_range(emp.id, start, work_date)
            short_days = [
                r
                for r in records
                if r.status in {"present", "missing_checkout"}
                and (r.work_duration_hours or Decimal("0")) < self._ctx.min_working_hours
            ]
            if len(short_days) >= 3:
                results.append(
                    {
                        "employee_id": emp.id,
                        "employee_name": emp.name,
                        "short_day_count": len(short_days),
                        "dates": [r.work_date.isoformat() for r in short_days],
                        "records": [_record_evidence(r) for r in short_days],
                    }
                )
        return results

    def _consecutive_absences(self, work_date: date, streak: int = 2) -> list[dict]:
        results: list[dict] = []
        for emp in self._employees.list_active():
            records = self._attendance.list_for_employee_range(
                emp.id, work_date - timedelta(days=14), work_date
            )
            records = sorted(records, key=lambda r: r.work_date, reverse=True)
            count = 0
            streak_records = []
            for record in records:
                if record.status == "absent":
                    count += 1
                    streak_records.append(_record_evidence(record))
                else:
                    break
            if count >= streak:
                results.append(
                    {
                        "employee_id": emp.id,
                        "employee_name": emp.name,
                        "consecutive_absent_days": count,
                        "records": streak_records,
                    }
                )
        return results

    def _build_alerts(
        self,
        work_date: date,
        records,
        *,
        ingest_errors: list[str],
        ingest_upserted: int,
        below_hours: list[dict],
        missing_checkout: list[dict],
        absent: list[dict],
        extremely_short: list[dict],
        consecutive_absences: list[dict],
    ) -> list[SmartAlert]:
        alerts: list[SmartAlert] = []

        for row in records:
            if row.status != "absent" and not row.check_in:
                alerts.append(
                    SmartAlert(
                        work_date=work_date,
                        employee_id=row.employee_id,
                        alert_type="missing_check_in",
                        severity="high",
                        message=f"Missing check-in for {row.employee.name if row.employee else row.employee_id}",
                        evidence=_record_evidence(row),
                    )
                )
            if row.status == "missing_checkout" or (row.check_in and not row.check_out):
                alerts.append(
                    SmartAlert(
                        work_date=work_date,
                        employee_id=row.employee_id,
                        alert_type="missing_check_out",
                        severity="high",
                        message=f"Missing check-out for {row.employee.name if row.employee else row.employee_id}",
                        evidence=_record_evidence(row),
                    )
                )
            if (
                row.status in {"present", "missing_checkout"}
                and (row.work_duration_hours or Decimal("0")) < self._ctx.min_working_hours
            ):
                alerts.append(
                    SmartAlert(
                        work_date=work_date,
                        employee_id=row.employee_id,
                        alert_type="work_hours_below_min",
                        severity="medium",
                        message=f"Below minimum hours for {row.employee.name if row.employee else row.employee_id}",
                        evidence=_record_evidence(row),
                    )
                )
            if row.work_duration_hours is not None and row.work_duration_hours < self._ctx.extremely_short_threshold:
                alerts.append(
                    SmartAlert(
                        work_date=work_date,
                        employee_id=row.employee_id,
                        alert_type="extremely_short_workday",
                        severity="medium",
                        message=f"Extremely short workday for {row.employee.name if row.employee else row.employee_id}",
                        evidence=_record_evidence(row),
                    )
                )

        for item in consecutive_absences:
            alerts.append(
                SmartAlert(
                    work_date=work_date,
                    employee_id=item["employee_id"],
                    alert_type="consecutive_absences",
                    severity="high",
                    message=f"{item['employee_name']} has {item['consecutive_absent_days']} consecutive absences",
                    evidence={"records": item["records"]},
                )
            )

        for error in ingest_errors:
            alerts.append(
                SmartAlert(
                    work_date=work_date,
                    employee_id=None,
                    alert_type="invalid_attendance_record",
                    severity="low",
                    message=error,
                    evidence={"ingest_error": error},
                )
            )

        if ingest_upserted > 0:
            alerts.append(
                SmartAlert(
                    work_date=work_date,
                    employee_id=None,
                    alert_type="duplicate_attendance_record",
                    severity="low",
                    message=f"{ingest_upserted} attendance record(s) updated from duplicate export rows",
                    evidence={"upserted": ingest_upserted},
                )
            )

        return alerts

    def _build_recommendations(
        self,
        work_date: date,
        *,
        below_hours: list[dict],
        missing_checkout: list[dict],
        absent: list[dict],
        repeated_short: list[dict],
        consecutive_absences: list[dict],
    ) -> list[AiRecommendation]:
        """Factual findings derived from attendance data — no speculative HR advice."""

        def _finding(title: str, fact: str, *, employee_id: int | None, evidence: dict, confidence: str):
            return AiRecommendation(
                work_date=work_date,
                employee_id=employee_id,
                title=title,
                reason=fact,
                recommendation=fact,
                confidence=confidence,
                evidence=evidence,
            )

        recommendations: list[AiRecommendation] = []

        for item in repeated_short:
            fact = (
                f"{item['employee_name']} worked below {self._ctx.min_working_hours} hours "
                f"on {item['short_day_count']} day(s) in the last 7 days."
            )
            recommendations.append(
                _finding(
                    f"Repeated short workdays — {item['employee_name']}",
                    fact,
                    employee_id=item["employee_id"],
                    evidence={"attendance_records": item["records"]},
                    confidence="high" if item["short_day_count"] >= 4 else "medium",
                )
            )

        week_start = work_date - timedelta(days=work_date.weekday())
        absent_this_week: dict[int, list[dict]] = {}
        for row in absent:
            row_date = date.fromisoformat(row["work_date"])
            if row_date >= week_start:
                absent_this_week.setdefault(row["employee_id"], []).append(row)

        for employee_id, rows in absent_this_week.items():
            if len(rows) < 2:
                continue
            name = rows[0].get("employee_name") or "Employee"
            fact = f"{name} was marked absent {len(rows)} time(s) this week."
            recommendations.append(
                _finding(
                    f"Repeated absences — {name}",
                    fact,
                    employee_id=employee_id,
                    evidence={"attendance_records": rows},
                    confidence="high",
                )
            )

        for item in consecutive_absences:
            fact = (
                f"{item['employee_name']} was absent {item['consecutive_absent_days']} "
                "consecutive day(s) ending on this date."
            )
            recommendations.append(
                _finding(
                    f"Consecutive absences — {item['employee_name']}",
                    fact,
                    employee_id=item["employee_id"],
                    evidence={"attendance_records": item["records"]},
                    confidence="high",
                )
            )

        if missing_checkout:
            fact = f"{len(missing_checkout)} employee(s) have missing check-out on {work_date.isoformat()}."
            recommendations.append(
                _finding(
                    "Missing check-outs",
                    fact,
                    employee_id=None,
                    evidence={"attendance_records": missing_checkout},
                    confidence="high",
                )
            )

        if below_hours and not repeated_short:
            fact = (
                f"{len(below_hours)} employee(s) worked below {self._ctx.min_working_hours} hours "
                f"on {work_date.isoformat()}."
            )
            recommendations.append(
                _finding(
                    "Short workdays",
                    fact,
                    employee_id=None,
                    evidence={"attendance_records": below_hours},
                    confidence="medium",
                )
            )

        if absent:
            fact = f"{len(absent)} employee(s) were marked absent on {work_date.isoformat()}."
            recommendations.append(
                _finding(
                    "Absences recorded",
                    fact,
                    employee_id=None,
                    evidence={"attendance_records": absent},
                    confidence="medium",
                )
            )

        return recommendations

    def _build_executive_summary(
        self,
        work_date: date,
        *,
        summary: dict,
        attention_names: list[str],
        recommendations: list[AiRecommendation],
        ignored_records: list[dict] | None = None,
    ) -> dict:
        finding_lines = [r.reason for r in recommendations[:5]]
        ignored_records = ignored_records or []
        lines = [
            "Today's Attendance Summary",
            "",
            f"Present: {summary['employees_present']}",
            f"Absent: {summary['employees_absent']}",
            f"Below {self._ctx.min_working_hours} Hours: {summary['employees_below_min_hours']}",
            f"Missing Checkout: {summary['employees_missing_checkout']}",
            f"Estimated Salary Deduction: ₹{summary['total_deductions']}",
            "",
            "Employees requiring attention:",
            "",
        ]
        if attention_names:
            lines.extend(f"• {name}" for name in attention_names)
        else:
            lines.append("• None")
        lines.extend(["", "Key Findings:", ""])
        if finding_lines:
            lines.extend(f"• {line}" for line in finding_lines)
        else:
            lines.append("• No anomalies detected for this date.")

        if ignored_records:
            lines.extend(["", "Warnings", ""])
            count = len(ignored_records)
            lines.append(
                f"{count} attendance record{'s' if count != 1 else ''} "
                "ignored because the employee is not registered."
            )
            for item in ignored_records[:10]:
                code = item.get("employee_code") or "unknown"
                lines.append(f"• Employee ID {code}: attendance record ignored.")

        text = "\n".join(lines)
        return {
            "work_date": work_date,
            "summary_text": text,
            "estimated_deductions": summary["total_deductions"],
            "payload": {
                "present": summary["employees_present"],
                "absent": summary["employees_absent"],
                "below_min_hours": summary["employees_below_min_hours"],
                "missing_checkout": summary["employees_missing_checkout"],
                "employees_requiring_attention": attention_names,
                "key_findings": finding_lines,
                "ignored_records": ignored_records,
            },
        }
