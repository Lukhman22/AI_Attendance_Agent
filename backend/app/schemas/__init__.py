from datetime import date, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..payroll.salary_resolver import resolve_salary_value


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


from .attendance_annotation import AttendanceAnnotationBase, AttendanceAnnotationRead, AttendanceAnnotationUpsert


class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    department: str | None = None
    working_days_per_month: int = 26

class EmployeeSalaryBase(BaseModel):
    employee_id: str
    employee_name: str | None = None
    monthly_salary: Decimal

class EmployeeSalaryCreate(EmployeeSalaryBase):
    pass

class EmployeeSalaryUpdate(BaseModel):
    monthly_salary: Decimal

class EmployeeSalaryRead(EmployeeSalaryBase, ORMModel):
    id: int
    effective_from: date | None = None



class EmployeeRead(ORMModel):
    id: int
    employee_code: str
    name: str
    department: str | None
    working_days_per_month: int
    is_active: bool
    attendance_percentage: float = 0.0


class AttendanceRecordRead(ORMModel):
    id: int
    employee_id: int
    work_date: date
    check_in: time | None
    check_out: time | None
    work_duration_hours: Decimal | None
    break_duration_hours: Decimal | None
    overtime_hours: Decimal | None
    status: str
    missing_hours: Decimal
    daily_deduction: Decimal
    source: str
    employee: EmployeeRead | None = None


class AttendanceIngestResult(BaseModel):
    imported: int
    upserted: int
    skipped: int
    ignored: int = 0
    employees_processed: int = 0
    errors: list[str] = Field(default_factory=list)
    ignored_records: list[dict[str, Any]] = Field(default_factory=list)
    salary_warnings: list[str] = Field(default_factory=list)


class DailySummaryResponse(BaseModel):
    work_date: date
    employees_present: int
    employees_absent: int
    employees_below_min_hours: int
    employees_missing_checkout: int
    total_deductions: Decimal
    details: dict[str, Any] = Field(default_factory=dict)


class AttendanceStatsResponse(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    present_days: int
    absent_days: int
    weekly_offs: int
    leave_days: int
    holidays: int
    total_worked_hours: Decimal
    average_daily_hours: Decimal
    attendance_percentage: Decimal


class PayrollRead(ORMModel):
    id: int
    employee_id: int
    year: int
    month: int
    present_days: int
    absent_days: int
    leave_days: int
    weekly_offs: int
    holidays: int
    working_days: int
    total_hours_worked: Decimal
    missing_hours: Decimal
    salary_deduction: Decimal
    final_salary: Decimal
    status: str
    employee: EmployeeRead | None = None


class PayrollGenerateRequest(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)


class NotificationSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class NotificationLogRead(ORMModel):
    id: int
    provider: str
    recipient: str | None
    message: str
    status: str
    error_detail: str | None


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(description="daily_summary | monthly_payroll | attendance_stats")
    format: str = Field(description="csv | excel | pdf")
    work_date: date | None = None
    year: int | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    start_date: date | None = None
    end_date: date | None = None


class ReportGenerateResponse(BaseModel):
    path: str
    filename: str
    format: str
    report_type: str


class AiDailyInsightRead(ORMModel):
    id: int
    work_date: date
    employees_present: int
    employees_absent: int
    employees_below_min_hours: int
    employees_missing_checkout: int
    total_deductions: Decimal
    payload: dict[str, Any]
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class AiMonthlyInsightRead(ORMModel):
    id: int
    year: int
    month: int
    company_attendance_percentage: Decimal
    average_daily_hours: Decimal
    total_salary_deductions: Decimal
    payload: dict[str, Any]


class SmartAlertRead(ORMModel):
    id: int
    work_date: date
    employee_id: int | None
    alert_type: str
    severity: str
    message: str
    evidence: dict[str, Any]
    status: str
    employee: EmployeeRead | None = None


class AiRecommendationRead(ORMModel):
    id: int
    work_date: date
    employee_id: int | None
    title: str
    reason: str
    recommendation: str
    confidence: str
    evidence: dict[str, Any]
    employee: EmployeeRead | None = None


class ExecutiveSummaryRead(ORMModel):
    id: int
    work_date: date
    summary_text: str
    estimated_deductions: Decimal
    payload: dict[str, Any]
    recommendations: list[AiRecommendationRead] = Field(default_factory=list)
    alerts: list[SmartAlertRead] = Field(default_factory=list)


class AiAskContext(BaseModel):
    work_date: date | None = None
    year: int | None = None
    month: int | None = None
    employee_id: int | None = None
    compare_employee_id: int | None = None
    intent: str | None = None
    granularity: str | None = None
    input_source: str | None = None

class AiAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    context: AiAskContext | None = None


class AiAskResponse(BaseModel):
    question: str
    answer: str
    references: dict[str, Any] = Field(default_factory=dict)
    context: AiAskContext | None = None
