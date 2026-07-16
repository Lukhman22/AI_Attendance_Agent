from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..config import Settings
from ..core.exceptions import ApplicationError
from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..database.repositories import IgnoredAttendanceRepository
from ..payroll.payroll_generator import PayrollGenerator
import calendar as cal


class ReportService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._reports_dir = Path(settings.reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        *,
        report_type: str,
        fmt: str,
        work_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, str]:
        fmt = fmt.lower()
        if fmt not in {"csv", "excel", "pdf"}:
            raise ApplicationError("Unsupported report format", code="report_format_invalid")

        rows = self._build_rows(
            report_type=report_type,
            work_date=work_date,
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
        )
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{report_type}_{stamp}"
        if fmt == "csv":
            path = self._write_csv(filename_base, rows)
        elif fmt == "excel":
            path = self._write_excel(filename_base, rows)
        else:
            path = self._write_pdf(filename_base, rows, title=report_type.replace("_", " ").title())

        return {
            "path": str(path.resolve()),
            "filename": path.name,
            "format": fmt,
            "report_type": report_type,
        }

    def resolve_download_path(self, filename: str) -> Path:
        safe_name = Path(filename).name
        if not safe_name or safe_name != filename:
            raise ApplicationError("Invalid report filename", code="report_filename_invalid")
        path = (self._reports_dir / safe_name).resolve()
        reports_root = self._reports_dir.resolve()
        if reports_root not in path.parents:
            raise ApplicationError("Invalid report filename", code="report_filename_invalid")
        if not path.is_file():
            raise ApplicationError("Report not found", code="report_not_found")
        return path

    def _build_rows(
        self,
        *,
        report_type: str,
        work_date: date | None,
        year: int | None,
        month: int | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[dict[str, Any]]:
        ignored_repo = IgnoredAttendanceRepository(self._db)

        if report_type == "daily_summary":
            if work_date is None:
                raise ApplicationError("work_date is required for daily_summary", code="report_params_invalid")
            summary = DailySummaryService(self._db).build(
                work_date, min_working_hours=Decimal(str(self._settings.min_working_hours))
            )
            rows = [
                {
                    "work_date": summary["work_date"],
                    "employees_present": summary["employees_present"],
                    "employees_absent": summary["employees_absent"],
                    "employees_below_min_hours": summary["employees_below_min_hours"],
                    "employees_missing_checkout": summary["employees_missing_checkout"],
                    "total_deductions": summary["total_deductions"],
                    "employee_id": "",
                    "reason": "",
                }
            ]
            return self._append_ignored_section(
                rows,
                [
                    {"employee_id": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_date(work_date)
                ],
            )

        if report_type == "monthly_payroll":
            if year is None or month is None:
                raise ApplicationError(
                    "year and month are required for monthly_payroll",
                    code="report_params_invalid",
                )
            generator = PayrollGenerator(self._db, settings=self._settings)
            records = generator.list_month(year, month)
            if not records:
                records = generator.generate_month(year, month)
            rows = [
                {
                    "employee_name": r.employee.name if r.employee else r.employee_id,
                    "present_days": r.present_days,
                    "absent_days": r.absent_days,
                    "leave_days": r.leave_days,
                    "working_days": r.working_days,
                    "total_hours_worked": r.total_hours_worked,
                    "missing_hours": r.missing_hours,
                    "salary_deduction": r.salary_deduction,
                    "final_salary": r.final_salary,
                    "employee_id": "",
                    "reason": "",
                }
                for r in records
            ]
            start = date(year, month, 1)
            end = date(year, month, cal.monthrange(year, month)[1])
            return self._append_ignored_section(
                rows,
                [
                    {"employee_id": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_range(start, end)
                ],
            )

        if report_type == "attendance_stats":
            if start_date is None or end_date is None:
                raise ApplicationError(
                    "start_date and end_date are required for attendance_stats",
                    code="report_params_invalid",
                )
            rows = AnalyticsService(self._db, self._settings).attendance_stats(start_date, end_date)
            padded = [{**row, "employee_id": "", "reason": ""} for row in rows]
            return self._append_ignored_section(
                padded,
                [
                    {"employee_id": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_range(start_date, end_date)
                ],
            )

        raise ApplicationError("Unsupported report_type", code="report_type_invalid")

    @staticmethod
    def _append_ignored_section(
        rows: list[dict[str, Any]],
        ignored: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        if not ignored:
            return rows
        if not rows:
            return [
                {"section": "Ignored Attendance Records", "employee_id": item["employee_id"], "reason": item["reason"]}
                for item in ignored
            ]

        keys = list(rows[0].keys())
        for key in ("section", "employee_id", "reason"):
            if key not in keys:
                keys.append(key)
                for row in rows:
                    row.setdefault(key, "")

        output = list(rows)
        header = {key: "" for key in keys}
        header["section"] = "Ignored Attendance Records"
        header["employee_id"] = "Employee ID"
        header["reason"] = "Reason"
        output.append(header)
        for item in ignored:
            line = {key: "" for key in keys}
            line["section"] = "ignored"
            line["employee_id"] = item["employee_id"]
            line["reason"] = item["reason"]
            output.append(line)
        return output

    def _write_csv(self, filename_base: str, rows: list[dict[str, Any]]) -> Path:
        path = self._reports_dir / f"{filename_base}.csv"
        fieldnames = list(rows[0].keys()) if rows else ["message"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            if rows:
                writer.writerows({k: self._stringify(v) for k, v in row.items()} for row in rows)
            else:
                writer.writerow({"message": "No data"})
        return path

    def _write_excel(self, filename_base: str, rows: list[dict[str, Any]]) -> Path:
        path = self._reports_dir / f"{filename_base}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Report"
        if not rows:
            sheet.append(["message"])
            sheet.append(["No data"])
        else:
            headers = list(rows[0].keys())
            sheet.append(headers)
            for row in rows:
                sheet.append([self._stringify(row.get(h)) for h in headers])
        workbook.save(path)
        return path

    def _write_pdf(self, filename_base: str, rows: list[dict[str, Any]], *, title: str) -> Path:
        path = self._reports_dir / f"{filename_base}.pdf"
        document = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=24, rightMargin=24)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Heading1"]), Spacer(1, 12)]

        if not rows:
            story.append(Paragraph("No data", styles["Normal"]))
        else:
            headers = list(rows[0].keys())
            data = [headers]
            for row in rows:
                data.append([self._stringify(row.get(h)) for h in headers])

            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)

        document.build(story)
        return path

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        return str(value)
