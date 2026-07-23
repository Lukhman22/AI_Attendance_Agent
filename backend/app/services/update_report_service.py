import re
from pathlib import Path

path = Path("/Users/mohammedlukhmaan/Desktop/AI_Attendance_Agent/backend/app/services/report_service.py")
content = path.read_text()

# 1. Update imports
content = content.replace(
    "from ..database.repositories import IgnoredAttendanceRepository, AttendanceRepository",
    "from ..database.repositories import IgnoredAttendanceRepository, AttendanceRepository, AttendanceAnnotationRepository"
)

# 2. Update HEADER_MAPPING
content = content.replace('    "employee_id": "Employee ID / Code",\n', '')

# 3. Update _build_rows
# Add annotation_repo
content = content.replace(
    "ignored_repo = IgnoredAttendanceRepository(self._db)",
    "ignored_repo = IgnoredAttendanceRepository(self._db)\n        annotation_repo = AttendanceAnnotationRepository(self._db)"
)

# Update daily_summary rows
daily_old = """                    "daily_deduction": r.daily_deduction,
                    "employee_id": "",
                    "reason": "",
                }"""
daily_new = """                    "daily_deduction": r.daily_deduction,
                    "reason": annotations.get(r.employee_id, "-"),
                }"""
content = content.replace(daily_old, daily_new)

content = content.replace(
    "records = AttendanceRepository(self._db).list_for_date(work_date)",
    "records = AttendanceRepository(self._db).list_for_date(work_date)\n            annotations = {a.employee_id: a.annotation_type for a in annotation_repo.list_for_date(work_date)}"
)

# Update monthly_payroll rows
monthly_old = """                    "final_salary": r.final_salary,
                    "employee_id": "",
                    "reason": "",
                }"""
monthly_new = """                    "final_salary": r.final_salary,
                    "reason": "-",
                }"""
content = content.replace(monthly_old, monthly_new)

# Update attendance_stats padded
content = content.replace(
    'padded = [{**row, "employee_id": "", "reason": ""} for row in rows]',
    'padded = [{**row, "reason": "-"} for row in rows]'
)

# Update ignored sections
content = content.replace(
    '{"employee_id": r.employee_code, "reason": r.reason}',
    '{"employee_code": r.employee_code, "reason": r.reason}'
)

ignored_section_old = """        if not rows:
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
        return output"""

ignored_section_new = """        if not rows:
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
        return output"""
content = content.replace(ignored_section_old, ignored_section_new)

# 4. Add formatters and update excel/pdf writes
formatters = """    @staticmethod
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
"""

content = content.replace("    @staticmethod\n    def _stringify(value: Any) -> str:", formatters + "\n    @staticmethod\n    def _stringify(value: Any) -> str:")

content = content.replace(
    "sheet.append([self._stringify(row.get(k)) for k in keys])",
    "sheet.append(self._format_row_human(row, keys))"
)

content = content.replace(
    "data.append([Paragraph(self._stringify(row.get(k)), cell_style) for k in keys])",
    "data.append([Paragraph(v, cell_style) for v in self._format_row_human(row, keys)])"
)

# 5. Improve PDF layout headers
pdf_old = """        story = [Paragraph(title, styles["Heading1"]), Spacer(1, 12)]"""
pdf_new = """        
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
            fontSize=9,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=20
        )
        
        now = datetime.now()
        meta_text = f"Generated: {now.strftime('%B %d, %Y')} at {now.strftime('%I:%M %p')}"
        story = [
            Paragraph(title, title_style),
            Paragraph(meta_text, meta_style),
        ]"""
content = content.replace(pdf_old, pdf_new)


path.write_text(content)
print("Updated report_service.py")
