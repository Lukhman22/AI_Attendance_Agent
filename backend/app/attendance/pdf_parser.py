from __future__ import annotations

import logging
import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO

import fitz

from ..core.exceptions import ApplicationError
from ..utils import hours_to_decimal, parse_time
from .provider import RawAttendanceRow

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

def _parse_report_month(text: str) -> tuple[int, int] | None:
    m = re.search(r'(?i)Report Month\s*([A-Za-z]+)[\s\-]+(\d{4})', text)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        return year, MONTH_MAP.get(month_str)
    # Fallback generic matching if exact 'Report Month' label is missing
    m2 = re.search(r'(?i)(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)[\s\-]*(\d{4})', text)
    if m2:
        month_str = m2.group(1).lower()
        year = int(m2.group(2))
        return year, MONTH_MAP.get(month_str)
    return None


@dataclass
class EmployeeBlock:
    code: str | None = None
    name: str | None = None
    department: str | None = None
    year: int | None = None
    month: int | None = None
    in_times: list[str] = field(default_factory=list)
    out_times: list[str] = field(default_factory=list)
    work_durations: list[str] = field(default_factory=list)
    break_durations: list[str] = field(default_factory=list)
    ot_durations: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)

def read_pdf_attendance(file_obj: BinaryIO, filename: str) -> list[RawAttendanceRow]:
    try:
        # PyMuPDF fits from a memory stream
        data = file_obj.read()
        if not data:
            raise ApplicationError("Uploaded PDF is empty", code="attendance_file_empty")
        doc = fitz.open(stream=data, filetype="pdf")
    except ApplicationError:
        raise
    except Exception as exc:
        raise ApplicationError(
            "The uploaded PDF is not a supported biometric attendance report.",
            code="attendance_file_invalid",
            details=f"{type(exc).__name__}: {exc}",
        ) from exc

    blocks_data = []
    for page in doc:
        blocks = page.get_text("blocks")
        # sort blocks top to bottom, then left to right
        blocks.sort(key=lambda b: (b[1], b[0]))
        for b in blocks:
            if b[6] == 0:  # text block
                text = b[4].strip()
                if text:
                    blocks_data.append(text)
                    
    if not blocks_data:
        raise ApplicationError("Unable to detect attendance tables.", code="attendance_file_invalid")

    global_year = None
    global_month = None

    # Do a quick pass to find global month
    for text in blocks_data:
        rm = _parse_report_month(text)
        if rm:
            global_year, global_month = rm
            break

    employees: list[EmployeeBlock] = []
    current_emp = EmployeeBlock(year=global_year, month=global_month)
    
    # Track which label we are currently reading
    for text in blocks_data:
        # Check if this block starts a new employee
        if re.search(r'(?i)(?:Empcode|Employee Code|Employee ID|Employee No|Emp Code|Staff Code)\s*[:\-\n]', text):
            if current_emp.code:
                employees.append(current_emp)
            current_emp = EmployeeBlock(year=global_year, month=global_month)
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for i, line in enumerate(lines):
                if line.lower() in ["empcode", "employee code", "employee id", "employee no", "emp code", "staff code", "id"] and i + 1 < len(lines):
                    current_emp.code = lines[i+1]
                if line.lower() in ["name", "employee name", "emp name"] and i + 1 < len(lines):
                    current_emp.name = lines[i+1]
                    
        # Check for department
        if "Dept. Name\n" in text or re.search(r'(?i)Dept', text):
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for i, line in enumerate(lines):
                if line.lower() in ["dept. name", "department", "dept"] and i + 1 < len(lines):
                    current_emp.department = lines[i+1]
                    
        rm = _parse_report_month(text)
        if rm:
            current_emp.year, current_emp.month = rm
            
        # Parse Tabular Data (usually formatted as a vertical list of tokens in a block with a header)
        tokens = re.split(r'\s+', text)
        if not tokens: continue
        
        header = tokens[0].upper()
        if header in ["IN", "OUT", "WORK", "BREAK", "OT", "STATUS"]:
            vals = tokens[1:]
            if header == "IN": current_emp.in_times.extend(vals)
            if header == "OUT": current_emp.out_times.extend(vals)
            if header == "WORK": current_emp.work_durations.extend(vals)
            if header == "BREAK": current_emp.break_durations.extend(vals)
            if header == "OT": current_emp.ot_durations.extend(vals)
            if header == "STATUS": current_emp.statuses.extend(vals)

    # Append the last employee
    if current_emp.code or current_emp.name or current_emp.in_times or current_emp.statuses:
        employees.append(current_emp)

    if not employees:
        raise ApplicationError("Unable to detect attendance tables.", code="attendance_file_invalid")

    records: list[RawAttendanceRow] = []
    imported = 0
    skipped = 0
    skip_reasons = set()

    for idx, emp in enumerate(employees, start=1):
        missing = []
        if not emp.code: missing.append("Employee Code")
        if not emp.name: missing.append("Employee Name")
        if not emp.year or not emp.month: missing.append("Report Month")
        
        # Determine the maximum days we collected data for this employee
        max_len = max([
            len(emp.in_times), len(emp.out_times), 
            len(emp.work_durations), len(emp.statuses)
        ], default=0)
        if max_len == 0:
            missing.append("Attendance Rows")
            
        if missing:
            reason = f"Missing {', '.join(missing)}"
            skip_reasons.add(reason)
            logger.warning(
                "Employee section incomplete. Skipped block #%d. %s", 
                idx, reason
            )
            skipped += 1
            continue
            
        _, days_in_month = monthrange(emp.year, emp.month) # type: ignore
        
        for i in range(max_len):
            day = i + 1
            if day > days_in_month:
                break
                
            def get_val(lst):
                val = lst[i] if i < len(lst) else None
                if val in ["-", "--:--", "_", ""]:
                    return None
                return val

            in_val = get_val(emp.in_times)
            out_val = get_val(emp.out_times)
            work_val = get_val(emp.work_durations)
            break_val = get_val(emp.break_durations)
            ot_val = get_val(emp.ot_durations)
            status_val = get_val(emp.statuses)
            
            check_in = parse_time(in_val) if in_val else None
            check_out = parse_time(out_val) if out_val else None
            
            if not status_val and check_in:
                status_val = "P"
                
            work_date = date(emp.year, emp.month, day) # type: ignore
            
            records.append(
                RawAttendanceRow(
                    employee_code=emp.code, # type: ignore
                    employee_name=emp.name, # type: ignore
                    department=emp.department,
                    work_date=work_date,
                    check_in=check_in,
                    check_out=check_out,
                    work_duration_hours=hours_to_decimal(work_val) if work_val else None,
                    break_duration_hours=hours_to_decimal(break_val) if break_val else None,
                    overtime_hours=hours_to_decimal(ot_val) if ot_val else None,
                    status=status_val
                )
            )
        imported += 1

    if imported == 0 and skipped > 0:
        raise ApplicationError(
            "Employee section is incomplete.",
            code="attendance_file_invalid"
        )
        
    if skipped > 0:
        logger.info(
            "PDF Import Summary:\nImported:\n%d employees\nSkipped:\n%d employee(s)\nReason:\n%s", 
            imported, skipped, " | ".join(skip_reasons)
        )
    else:
        logger.info("PDF Import Summary: Imported: %d employees, Skipped: %d employees", imported, skipped)
        
    return records
