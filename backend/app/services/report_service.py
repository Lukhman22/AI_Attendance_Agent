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
from ..database.repositories import IgnoredAttendanceRepository, AttendanceRepository, AttendanceAnnotationRepository
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

        if report_type == "daily_summary":
            title = "Daily Attendance Report"
            report_period = f"Reporting Date: {work_date.strftime('%d %B %Y')}"
            filename_base = f"Daily_Attendance_{work_date.strftime('%d_%B_%Y')}"
        elif report_type == "monthly_payroll":
            title = "Monthly Payroll Report"
            month_name = date(year, month, 1).strftime('%B')
            report_period = f"Reporting Month: {month_name} {year}"
            filename_base = f"Monthly_Payroll_{month_name}_{year}"
        elif report_type == "attendance_stats":
            title = "Attendance Statistics Report"
            month_name = start_date.strftime('%B') if start_date else ""
            year_val = start_date.strftime('%Y') if start_date else ""
            report_period = f"Reporting Month: {month_name} {year_val}"
            filename_base = f"Attendance_Statistics_{month_name}_{year_val}"
        else:
            title = report_type.replace("_", " ").title()
            report_period = ""
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = f"{report_type}_{stamp}"

        rows, summary_data = self._build_rows(
            report_type=report_type,
            work_date=work_date,
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
        )

        if fmt == "csv":
            path = self._write_csv(filename_base, rows)
        elif fmt == "excel":
            path = self._write_excel(filename_base, rows, title=title, report_period=report_period, summary_data=summary_data)
        else:
            path = self._write_pdf(filename_base, rows, title=title, report_period=report_period, summary_data=summary_data)

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
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        ignored_repo = IgnoredAttendanceRepository(self._db)
        from sqlalchemy import func
        from ..models.Attendance import Attendance

        if report_type == "daily_summary":
            if work_date is None:
                raise ApplicationError("work_date is required for daily_summary", code="report_params_invalid")
            
            records = AttendanceRepository(self._db).list_for_date(work_date)
            
            # Validation: ensure records exist
            if not records:
                 raise ApplicationError("No data found for this date", code="no_data_found")

            present_count = sum(1 for r in records if r.status != "absent")
            absent_count = sum(1 for r in records if r.status == "absent")
            attendance_rate = (present_count / len(records) * 100) if records else 0

            summary_data = {
                "Total Employees": str(len(records)),
                "Present": str(present_count),
                "Absent": str(absent_count),
                "Attendance Rate": f"{attendance_rate:.1f}%",
            }

            rows = [
                {
                    "employee_code": r.employee.employee_code if r.employee else "",
                    "employee_name": r.employee.name if r.employee else "",
                    "department": r.employee.department if r.employee else "",
                    "check_in": r.check_in.isoformat() if r.check_in else "-",
                    "check_out": r.check_out.isoformat() if r.check_out else "-",
                    "work_duration_hours": r.work_duration_hours,
                    "break_duration_hours": r.break_duration_hours,
                    "overtime_hours": r.overtime_hours,
                    "status": r.status,
                    "daily_deduction": r.daily_deduction,
                    "reason": r.leave_reason if r.status == "absent" and r.leave_reason else "",
                }
                for r in records
            ]
            final_rows = self._append_ignored_section(
                rows,
                [
                    {"employee_code": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_date(work_date)
                ],
            )
            return final_rows, summary_data

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

            total_payroll = sum(r.final_salary for r in records if r.final_salary)
            total_deductions = sum(r.salary_deduction for r in records if r.salary_deduction)
            avg_salary = total_payroll / len(records) if records else 0

            summary_data = {
                "Employees Processed": str(len(records)),
                "Total Payroll": f"₹{total_payroll:,.2f}",
                "Total Deductions": f"₹{total_deductions:,.2f}",
                "Average Salary": f"₹{avg_salary:,.2f}",
            }
            
            start = date(year, month, 1)
            end = date(year, month, cal.monthrange(year, month)[1])

            # Pre-fetch leave reasons
            att_records = self._db.query(Attendance.employee_id, Attendance.leave_reason).filter(
                Attendance.work_date >= start,
                Attendance.work_date <= end,
                Attendance.status == "absent",
                Attendance.leave_reason.isnot(None)
            ).all()

            from collections import defaultdict
            reasons_by_emp = defaultdict(lambda: defaultdict(int))
            for emp_id, reason in att_records:
                if reason:
                    reasons_by_emp[emp_id][reason] += 1

            def format_reasons(emp_id: int) -> str:
                counts = reasons_by_emp.get(emp_id, {})
                if not counts: return ""
                parts = []
                for reason, count in counts.items():
                    parts.append(f"{reason} ({count})" if count > 1 else reason)
                return ", ".join(parts)

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
                    "reason": format_reasons(r.employee_id),
                }
                for r in records
            ]
            final_rows = self._append_ignored_section(
                rows,
                [
                    {"employee_code": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_range(start, end)
                ],
            )
            return final_rows, summary_data

        if report_type == "attendance_stats":
            if start_date is None or end_date is None:
                raise ApplicationError("start_date and end_date are required for attendance_stats", code="report_params_invalid")
            rows = AnalyticsService(self._db, self._settings).attendance_stats(start_date, end_date)
            
            # Validation: ensure stats exist
            if not rows:
                raise ApplicationError("No attendance stats found for this range", code="no_data_found")

            avg_attendance = sum(float(r.get("attendance_percentage", 0)) for r in rows) / len(rows) if rows else 0
            highest_emp = max(rows, key=lambda x: float(x.get("attendance_percentage", 0)))
            lowest_emp = min(rows, key=lambda x: float(x.get("attendance_percentage", 0)))

            summary_data = {
                "Total Employees": str(len(rows)),
                "Average Attendance": f"{avg_attendance:.1f}%",
                "Highest Attendance": f"{highest_emp.get('employee_name', '')} ({float(highest_emp.get('attendance_percentage', 0)):.1f}%)",
                "Lowest Attendance": f"{lowest_emp.get('employee_name', '')} ({float(lowest_emp.get('attendance_percentage', 0)):.1f}%)",
            }

            # Pre-fetch leave reasons
            att_records = self._db.query(Attendance.employee_id, Attendance.leave_reason).filter(
                Attendance.work_date >= start_date,
                Attendance.work_date <= end_date,
                Attendance.status == "absent",
                Attendance.leave_reason.isnot(None)
            ).all()

            from collections import defaultdict
            reasons_by_emp = defaultdict(lambda: defaultdict(int))
            for emp_id, reason in att_records:
                if reason:
                    reasons_by_emp[emp_id][reason] += 1

            def format_reasons(emp_id: int) -> str:
                counts = reasons_by_emp.get(emp_id, {})
                if not counts: return ""
                parts = []
                for reason, count in counts.items():
                    parts.append(f"{reason} ({count})" if count > 1 else reason)
                return ", ".join(parts)

            padded = []
            for row in rows:
                padded.append({
                    "employee_code": row.get("employee_code", ""),
                    "employee_name": row.get("employee_name", ""),
                    "present_days": row.get("present_days", 0),
                    "absent_days": row.get("absent_days", 0),
                    "total_worked_hours": row.get("total_worked_hours", 0),
                    "average_daily_hours": row.get("average_daily_hours", 0),
                    "attendance_percentage": row.get("attendance_percentage", 0),
                    "reason": format_reasons(row.get("employee_id", 0))
                })
            final_rows = self._append_ignored_section(
                padded,
                [
                    {"employee_code": r.employee_code, "reason": r.reason}
                    for r in ignored_repo.list_for_range(start_date, end_date)
                ],
            )
            return final_rows, summary_data

        raise ApplicationError("Unsupported report_type", code="report_type_invalid")

    @staticmethod
    def _append_ignored_section(rows: list[dict[str, Any]], ignored: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not ignored: return rows
        if not rows:
            return [{"section": "Ignored Attendance Records", "employee_code": item.get("employee_code", ""), "reason": item.get("reason", "")} for item in ignored]
        keys = list(rows[0].keys())
        for key in ("section", "employee_code", "reason"):
            if key not in keys:
                keys.append(key)
                for row in rows: row.setdefault(key, "")
        output = list(rows)
        header = {key: "" for key in keys}; header["section"] = "Ignored Attendance Records"; header["employee_code"] = "Employee ID"; header["reason"] = "Reason"
        output.append(header)
        for item in ignored:
            line = {key: "" for key in keys}; line["section"] = "ignored"; line["employee_code"] = item.get("employee_code", ""); line["reason"] = item.get("reason", "")
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

    def _write_excel(self, filename_base: str, rows: list[dict[str, Any]], *, title: str = "", report_period: str = "", summary_data: dict[str, str] = None) -> Path:
        path = self._reports_dir / f"{filename_base}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Report"
        
        keys = list(rows[0].keys()) if rows else []
        display_headers = [HEADER_MAPPING.get(k, k.replace("_", " ").title()) for k in keys]
        
        formatted_rows = []
        for row in rows:
            formatted_rows.append(self._format_row_human(row, keys))
            
        from ..utils.excel import format_excel_report
        return format_excel_report(
            workbook=workbook,
            sheet=sheet,
            title=title,
            report_period=report_period,
            summary_data=summary_data or {},
            headers=display_headers,
            rows=formatted_rows,
            filename=path
        )

    def _write_pdf(self, filename_base: str, rows: list[dict[str, Any]], *, title: str, report_period: str = "", summary_data: dict[str, str] = None) -> Path:
        path = self._reports_dir / f"{filename_base}.pdf"
        document = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=24, rightMargin=24)
        styles = getSampleStyleSheet()
        
        # Create styles so we don't mutate the same reference
        cell_style = ParagraphStyle(
            "cell_style",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            textColor=colors.black
        )
        
        header_style = ParagraphStyle(
            "header_style",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.white,
            fontName="Helvetica-Bold"
        )

        
        # Professional header
        title_style = ParagraphStyle(
            "title_style",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=6
        )
        meta_style = ParagraphStyle(
            "meta_style",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=6
        )
        summary_style = ParagraphStyle(
            "summary_style",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=15
        )
        
        now = datetime.now()
        meta_text = f"Generated On<br/>{now.strftime('%d %B %Y')}<br/>{now.strftime('%I:%M %p')}"
        
        header_table_data = [[
            Paragraph("<b>AI Attendance Agent</b><br/><br/>" + f"<font size=14><b>{title}</b></font>", title_style),
            Paragraph(f"<b>{report_period.split(': ')[0]}</b><br/>{report_period.split(': ')[1] if ': ' in report_period else ''}", meta_style) if report_period else "",
            Paragraph(meta_text, meta_style)
        ]]
        header_table = Table(header_table_data, colWidths=[400, 150, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (2, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))

        story = [header_table]
        
        if summary_data:
            summary_parts = []
            for k, v in summary_data.items():
                summary_parts.append(f"<b>{k}:</b><br/>{v}")
            
            # Divide summary parts evenly across row
            sum_row = [Paragraph(part, summary_style) for part in summary_parts]
            sum_table = Table([sum_row], colWidths=[794 / len(sum_row)] * len(sum_row))
            sum_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ]))
            story.append(sum_table)
        
        keys = list(rows[0].keys()) if rows else []
        display_headers = [HEADER_MAPPING.get(k, k.replace("_", " ").title()) for k in keys]
        
        data = [[Paragraph(h, header_style) for h in display_headers]]
        for row in rows:
            data.append([Paragraph(v, cell_style) for v in self._format_row_human(row, keys)])
            
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Number of rows: {len(rows)}")
        logger.debug(f"Number of columns: {len(keys)}")
        logger.debug(f"First data row: {rows[0] if rows else 'None'}")
        logger.debug(f"Table data length: {len(data)}")
            
        # Proportional columns to expand across A4 landscape (842pt - 48pt margins = 794pt)
        usable_width = 794
        col_widths = [usable_width / len(keys)] * len(keys) if keys else None
        
        # Fine-tune if it's the exact 8-column stats layout
        if len(keys) == 8:
            col_widths = [80, 140, 75, 75, 95, 95, 85, 149]
            
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        document.build(story)
        return path

    @staticmethod
    def _format_hours(value: Any) -> str:
        if value is None or value == "":
            return ""
        try:
            val = float(value)
            if val == 0:
                return "0m"
            hours = int(val)
            minutes = int(round((val - hours) * 60))
            if minutes == 60:
                hours += 1
                minutes = 0
            if hours > 0 and minutes > 0:
                return f"{hours}h {minutes:02d}m"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_status(status: Any) -> str:
        if not status:
            return ""
        return str(status).replace("_", " ").title()

    def _format_row_human(self, row: dict[str, Any], keys: list[str]) -> list[str]:
        formatted = []
        for k in keys:
            val = row.get(k)
            if k in ["work_duration_hours", "break_duration_hours", "overtime_hours", "total_hours_worked", "missing_hours", "average_daily_hours"]:
                formatted.append(self._format_hours(val))
            elif k == "status":
                formatted.append(self._format_status(val))
            else:
                formatted.append(self._stringify(val))
        return formatted

    @staticmethod
    def _stringify(value: Any) -> str:
        return str(value) if value is not None else ""