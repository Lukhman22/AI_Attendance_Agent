from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from ..config import Settings
from ..core.exceptions import ApplicationError
from ..dashboard.analytics import AnalyticsService
from ..dashboard.summary import DailySummaryService
from ..database.repositories import IgnoredAttendanceRepository, AttendanceRepository
from ..payroll.payroll_generator import PayrollGenerator
import calendar as cal

HEADER_MAPPING = {
    "employee_code": "Employee ID",
    "employee_name": "Employee Name",
    "department": "Department",
    "check_in": "Check In",
    "check_out": "Check Out",
    "work_duration_hours": "Work Hours",
    "break_duration_hours": "Break Hours",
    "overtime_hours": "Overtime Hours",
    "status": "Status",
    "daily_deduction": "Daily Deduction",
    "salary_deduction": "Salary Deduction",
    "final_salary": "Final Salary",
    "present_days": "Present Days",
    "absent_days": "Absent Days",
    "leave_days": "Leave Days",
    "working_days": "Working Days",
    "weekly_offs": "Weekly Offs",
    "holidays": "Holidays",
    "total_hours_worked": "Total Hours Worked",
    "total_worked_hours": "Total Worked Hours",
    "average_daily_hours": "Average Daily Hours",
    "attendance_percentage": "Attendance %",
    "work_date": "Date",
    "employee_id": "Employee ID / Code",
    "reason": "Reason",
    "section": "Section",
    "missing_hours": "Missing Hours",
}

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
            
            records = AttendanceRepository(self._db).list_for_date(work_date)
            
            # Validation: ensure records exist
            if not records:
                 raise ApplicationError("No data found for this date", code="no_data_found")

            rows = [
                {
                    "employee_code": r.employee.employee_code if r.employee else "",
                    "employee_name": r.employee.name if r.employee else "",
                    "department": r.employee.department if r.employee else "",
                    "check_in": r.check_in.isoformat() if r.check_in else "",
                    "check_out": r.check_out.isoformat() if r.check_out else "",
                    "work_duration_hours": r.work_duration_hours,
                    "break_duration_hours": r.break_duration_hours,
                    "overtime_hours": r.overtime_hours,
                    "status": r.status,
                    "daily_deduction": r.daily_deduction,
                    "employee_id": "",
                    "reason": "",
                }
                for r in records
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
                raise ApplicationError("year and month are required for monthly_payroll", code="report_params_invalid")
            generator = PayrollGenerator(self._db, settings=self._settings)
            records = generator.list_month(year, month)
            if not records:
                records = generator.generate_month(year, month)
            
            # Validation: ensure records exist
            if not records:
                raise ApplicationError("No payroll records found for this period", code="no_data_found")

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
                raise ApplicationError("start_date and end_date are required for attendance_stats", code="report_params_invalid")
            rows = AnalyticsService(self._db, self._settings).attendance_stats(start_date, end_date)
            
            # Validation: ensure stats exist
            if not rows:
                raise ApplicationError("No attendance stats found for this range", code="no_data_found")

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
    def _append_ignored_section(rows: list[dict[str, Any]], ignored: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not ignored: return rows
        if not rows:
            return [{"section": "Ignored Attendance Records", "employee_id": item["employee_id"], "reason": item["reason"]} for item in ignored]
        keys = list(rows[0].keys())
        for key in ("section", "employee_id", "reason"):
            if key not in keys:
                keys.append(key)
                for row in rows: row.setdefault(key, "")
        output = list(rows)
        header = {key: "" for key in keys}; header["section"] = "Ignored Attendance Records"; header["employee_id"] = "Employee ID"; header["reason"] = "Reason"
        output.append(header)
        for item in ignored:
            line = {key: "" for key in keys}; line["section"] = "ignored"; line["employee_id"] = item["employee_id"]; line["reason"] = item["reason"]
            output.append(line)
        return output

    def _write_csv(self, filename_base: str, rows: list[dict[str, Any]]) -> Path:
        path = self._reports_dir / f"{filename_base}.csv"
        keys = list(rows[0].keys()) if rows else []
        display_headers = [HEADER_MAPPING.get(k, k.replace("_", " ").title()) for k in keys]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if display_headers:
                writer.writerow(display_headers)
            for row in rows:
                writer.writerow([self._stringify(row.get(k)) for k in keys])
        return path

    def _write_excel(self, filename_base: str, rows: list[dict[str, Any]]) -> Path:
        path = self._reports_dir / f"{filename_base}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Report"
        
        keys = list(rows[0].keys()) if rows else []
        display_headers = [HEADER_MAPPING.get(k, k.replace("_", " ").title()) for k in keys]
        
        if display_headers:
            sheet.append(display_headers)
            
        for row in rows:
            sheet.append([self._stringify(row.get(k)) for k in keys])
            
        # Professional styling
        if rows:
            from openpyxl.styles import Font, Alignment, PatternFill
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
            body_font = Font(name="Calibri", size=11, color="000000")
            body_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            
            # Style header
            for col_idx in range(1, len(keys) + 1):
                cell = sheet.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
            # Style body
            for row_idx in range(2, len(rows) + 2):
                for col_idx in range(1, len(keys) + 1):
                    cell = sheet.cell(row=row_idx, column=col_idx)
                    cell.font = body_font
                    cell.fill = body_fill
                
            # Adjust column widths
            for col in sheet.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 10)
                
        workbook.save(path)
        return path

    def _write_pdf(self, filename_base: str, rows: list[dict[str, Any]], *, title: str) -> Path:
        path = self._reports_dir / f"{filename_base}.pdf"
        document = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=24, rightMargin=24)
        styles = getSampleStyleSheet()
        
        # Create styles so we don't mutate the same reference
        cell_style = ParagraphStyle(
            "cell_style",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.black
        )
        
        header_style = ParagraphStyle(
            "header_style",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName="Helvetica-Bold"
        )

        story = [Paragraph(title, styles["Heading1"]), Spacer(1, 12)]
        
        keys = list(rows[0].keys()) if rows else []
        display_headers = [HEADER_MAPPING.get(k, k.replace("_", " ").title()) for k in keys]
        
        data = [[Paragraph(h, header_style) for h in display_headers]]
        for row in rows:
            data.append([Paragraph(self._stringify(row.get(k)), cell_style) for k in keys])
            
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Number of rows: {len(rows)}")
        logger.debug(f"Number of columns: {len(keys)}")
        logger.debug(f"First data row: {rows[0] if rows else 'None'}")
        logger.debug(f"Table data length: {len(data)}")
            
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        document.build(story)
        return path

    @staticmethod
    def _stringify(value: Any) -> str:
        return str(value) if value is not None else ""