from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session

from ..config import Settings
from ..config.settings import settings
from ..core.exceptions import ApplicationError
from ..database.repositories import NotificationRepository
from ..models import Attendance, Employee, NotificationSettings, Payroll
from ..notifications import (
    NotificationProvider,
    TelegramNotificationProvider,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._repo = NotificationRepository(db)
        self._provider = self._resolve_provider(settings)

    def _resolve_provider(self, settings: Settings) -> NotificationProvider | None:
        if settings.notification_provider == "telegram":
            # Check DB settings
            db_settings = self._db.query(NotificationSettings).first()
            if db_settings and db_settings.telegram_enabled and db_settings.telegram_bot_token and db_settings.telegram_chat_id:
                return TelegramNotificationProvider(
                    token=db_settings.telegram_bot_token, 
                    chat_id=db_settings.telegram_chat_id
                )
        return None

    def send(self, message: str, *, recipient: str | None = None) -> dict:
        if self._provider is None:
            raise ApplicationError(
                "No notification provider configured (set NOTIFICATION_PROVIDER)",
                code="notification_provider_disabled",
            )

        result = self._provider.send(message, recipient=recipient)
        log = self._repo.create(
            provider=result.provider,
            message=message,
            recipient=recipient,
            status="sent" if result.success else "failed",
            error_detail=result.error,
        )
        self._db.commit()
        if not result.success:
            logger.warning("Notification failed via %s: %s", result.provider, result.error)
            raise ApplicationError(
                "Failed to send notification",
                code="notification_send_failed",
                details=result.error,
            )
        return {
            "id": log.id,
            "provider": log.provider,
            "status": log.status,
            "message": log.message,
        }

    def list_recent(self, limit: int = 50) -> list:
        return self._repo.list_recent(limit)


# --- NEW NOTIFICATION CENTER FUNCTIONS ---

def _dispatch_message(db: Session, message: str) -> dict:
    """Helper function to route the message to enabled providers from DB settings."""
    db_settings = db.query(NotificationSettings).first()
    if not db_settings:
        return {"status": "skipped", "reason": "No notification settings found."}

    repo = NotificationRepository(db)
    dispatched_to = []

    # Send via Telegram if enabled
    if db_settings.telegram_enabled and db_settings.telegram_chat_id:
        try:
            telegram_provider = TelegramNotificationProvider(
                token=db_settings.telegram_bot_token,
                chat_id=db_settings.telegram_chat_id,
            )
            result = telegram_provider.send(message, recipient=db_settings.telegram_chat_id)
            repo.create(
                provider=result.provider,
                message=message,
                recipient=db_settings.telegram_chat_id,
                status="sent" if result.success else "failed",
                error_detail=result.error,
            )
            db.commit()
            if result.success:
                dispatched_to.append("Telegram")
        except Exception as e:
            logger.error(f"Telegram Dispatch Error: {e}")

    return {"dispatched_to": dispatched_to}


def send_daily_summary(db: Session, target_date: str | None = None) -> dict:
    """Generates and sends the daily attendance summary."""
    import datetime
    if not target_date:
        t_date = datetime.date.today()
    elif isinstance(target_date, str):
        t_date = datetime.date.fromisoformat(target_date)
    else:
        t_date = target_date
        
    msg = generate_daily_executive_report(db, t_date)
    return _dispatch_message(db, msg)


def send_monthly_payroll_summary(db: Session, month: int, year: int) -> dict:
    """Generates and sends the monthly payroll summary."""
    msg = generate_monthly_payroll_report(db, month, year)
    return _dispatch_message(db, msg)


def format_duration(decimal_hours: Decimal) -> str:
    from decimal import Decimal
    total_minutes = int(round(decimal_hours * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes:02d}m"


def format_currency(val: Decimal, include_decimal: bool = False) -> str:
    from decimal import Decimal
    if include_decimal:
        return f"₹{val:,.2f}"
    if val == int(val):
        return f"₹{int(val):,}"
    return f"₹{val:,.2f}"


def generate_daily_executive_report(db: Session, target_date: datetime.date) -> str:
    from decimal import Decimal
    from datetime import time, datetime, date
    from ..config import get_settings
    
    settings = get_settings()
    
    # 1. Fetch active employees
    all_employees = db.query(Employee).filter(Employee.is_active.is_(True)).all()
    total_employees = len(all_employees)
    
    # 2. Fetch attendances
    attendances = db.query(Attendance).filter(Attendance.work_date == target_date).all()
    
    # Map employee_id to Employee
    emp_map = {emp.id: emp for emp in all_employees}
    
    present_records = []
    present_emp_ids = set()
    excused_emp_ids = set()
    
    # Classify database records
    for att in attendances:
        status_clean = (att.status or '').strip().lower()
        if status_clean in {'present', 'missing_checkout'}:
            present_records.append(att)
            present_emp_ids.add(att.employee_id)
        elif status_clean in {'leave', 'weekly_off', 'holiday'}:
            excused_emp_ids.add(att.employee_id)
            
    # Absent today are active employees not present and not excused
    absent_employees = [emp for emp in all_employees if emp.id not in present_emp_ids and emp.id not in excused_emp_ids]
    absent_names = sorted([emp.name for emp in absent_employees])
    
    # Counts
    present_count = len(present_emp_ids)
    absent_count = len(absent_employees)
    
    # Late Arrivals count
    late_count = 0
    try:
        late_threshold = time.fromisoformat(settings.late_arrival_time)
    except Exception:
        late_threshold = time(9, 30)
        
    for att in attendances:
        status_clean = (att.status or '').strip().lower()
        if status_clean in {'present', 'missing_checkout'} and att.check_in:
            if att.check_in > late_threshold:
                late_count += 1
                
    # Missing Checkouts count
    missing_checkout_count = sum(1 for att in attendances if att.status.lower() == 'missing_checkout' or (att.check_in and not att.check_out))
    
    # Format Absent section
    if absent_names:
        absent_section = "\n".join(f"• {name}" for name in absent_names)
    else:
        absent_section = "No employees were absent today."
        
    # Format Least Working Hours section
    # present_records with work duration > 0, sorted ascending by work_duration_hours
    worked_records = [r for r in present_records if r.work_duration_hours and r.work_duration_hours > 0]
    worked_records_sorted = sorted(worked_records, key=lambda x: x.work_duration_hours or Decimal("0"))
    
    least_working_lines = []
    for idx, r in enumerate(worked_records_sorted, 1):
        emp_name = emp_map[r.employee_id].name if r.employee_id in emp_map else f"ID {r.employee_id}"
        least_working_lines.append(f"{idx}. {emp_name} — {format_duration(r.work_duration_hours)}")
        
    if least_working_lines:
        least_working_section = "\n".join(least_working_lines)
    else:
        least_working_section = "No employees worked today."
        
    # Format Employees Requiring Attention section
    # Include employees who: arrived late, worked less than minimum hours, forgot checkout, were absent
    attention_list = []
    
    # 1. Absentees
    for emp in absent_employees:
        attention_list.append((emp.name, ["Absent"]))
        
    # 2. Present/Missing checkout issues
    for att in attendances:
        status_clean = (att.status or '').strip().lower()
        if status_clean in {'present', 'missing_checkout'}:
            reasons = []
            emp_name = emp_map[att.employee_id].name if att.employee_id in emp_map else f"ID {att.employee_id}"
            
            # Late
            if att.check_in and att.check_in > late_threshold:
                diff_seconds = (datetime.combine(date.min, att.check_in) - datetime.combine(date.min, late_threshold)).total_seconds()
                late_minutes = int(round(diff_seconds / 60))
                if late_minutes > 0:
                    reasons.append(f"Late by {late_minutes} min")
            
            # Less than minimum hours
            min_hours = Decimal(str(settings.min_working_hours))
            worked = att.work_duration_hours or Decimal("0")
            if worked < min_hours:
                reasons.append(f"Worked only {format_duration(worked)}")
                
            # Missing checkout
            if att.status.lower() == 'missing_checkout' or (att.check_in and not att.check_out):
                reasons.append("Missing Checkout")
                
            if reasons:
                attention_list.append((emp_name, reasons))
                
    attention_list_sorted = sorted(attention_list, key=lambda x: x[0].lower())
    
    attention_lines = []
    for emp_name, reasons in attention_list_sorted:
        attention_lines.append(f"• {emp_name}")
        for r in reasons:
            attention_lines.append(f"   - {r}")
            
    if attention_lines:
        attention_section = "\n".join(attention_lines)
    else:
        attention_section = "No employees require attention today."
        
    # Format Best Performer section
    if worked_records:
        best_record = max(worked_records, key=lambda x: x.work_duration_hours or Decimal("0"))
        best_name = emp_map[best_record.employee_id].name if best_record.employee_id in emp_map else f"ID {best_record.employee_id}"
        best_performer_section = f"{best_name}\n{format_duration(best_record.work_duration_hours)}"
    else:
        best_performer_section = "No performers today."
        
    missing_checkout_str = "No missing check-outs." if missing_checkout_count == 0 else str(missing_checkout_count)

    msg = f"""========================
DAILY HR EXECUTIVE REPORT
========================

📅 Date: {target_date.isoformat()}

👥 Total Employees: {total_employees}
✅ Present: {present_count}
❌ Absent: {absent_count}
⏰ Late Arrivals: {late_count}
⚠️ Missing Checkouts: {missing_checkout_str}

------------------------------------------------

📌 Employees Absent Today

{absent_section}

------------------------------------------------

🕒 Employees with Least Working Hours

{least_working_section}

------------------------------------------------

⚠️ Employees Requiring Attention

{attention_section}

------------------------------------------------

🏆 Best Performer Today

{best_performer_section}

------------------------------------------------

Generated automatically by AI Attendance Agent."""
    return msg


def generate_monthly_payroll_report(db: Session, month: int, year: int) -> str:
    import calendar
    from decimal import Decimal
    
    payrolls = db.query(Payroll).filter(Payroll.month == month, Payroll.year == year).all()
    
    # Sort employees alphabetically
    payrolls_sorted = sorted(payrolls, key=lambda p: (p.employee.name if p.employee else '').lower())
    
    employees_processed = len(payrolls_sorted)
    
    total_payroll = sum([p.final_salary for p in payrolls_sorted if p.final_salary], Decimal("0.00"))
    total_deductions = sum([p.salary_deduction for p in payrolls_sorted if p.salary_deduction], Decimal("0.00"))
    
    try:
        month_name = calendar.month_name[month]
    except Exception:
        month_name = str(month)
    
    payroll_lines = []
    for p in payrolls_sorted:
        name = p.employee.name if p.employee else f"ID {p.employee_id}"
        salary_str = format_currency(p.final_salary)
        deduction_str = format_currency(p.salary_deduction)
        payroll_lines.append(f"{name}\nSalary : {salary_str}\nDeduction : {deduction_str}")
        
    payroll_section = "\n\n".join(payroll_lines) if payroll_lines else "No employee payroll processed."
    
    # Highest and Lowest salary
    if payrolls_sorted:
        highest_payroll = max(payrolls_sorted, key=lambda p: p.final_salary or Decimal("0"))
        lowest_payroll = min(payrolls_sorted, key=lambda p: p.final_salary or Decimal("0"))
        
        highest_name = highest_payroll.employee.name if highest_payroll.employee else f"ID {highest_payroll.employee_id}"
        highest_val = format_currency(highest_payroll.final_salary)
        
        lowest_name = lowest_payroll.employee.name if lowest_payroll.employee else f"ID {lowest_payroll.employee_id}"
        lowest_val = format_currency(lowest_payroll.final_salary)
        
        highest_section = f"{highest_name}\n{highest_val}"
        lowest_section = f"{lowest_name}\n{lowest_val}"
    else:
        highest_section = "N/A"
        lowest_section = "N/A"
        
    msg = f"""💰 Monthly Payroll Report
Month: {month_name} {year}

Employees Processed: {employees_processed}

--------------------------------

Employee Payroll

{payroll_section}

--------------------------------

Highest Salary
{highest_section}

Lowest Salary
{lowest_section}

--------------------------------

Total Payroll
{format_currency(total_payroll, include_decimal=True)}

Total Deductions
{format_currency(total_deductions, include_decimal=True)}

Payroll Generated Successfully

Generated automatically by AI Attendance Agent."""
    return msg