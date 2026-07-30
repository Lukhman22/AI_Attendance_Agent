export interface Employee {
  id: number
  employee_code: string
  name: string
  department: string | null
  working_days_per_month: number
  is_active: boolean
}

export interface AttendanceAnnotation {
  id: number
  employee_id: number
  work_date: string
  annotation_type: string
  notes?: string | null
  created_at: string
}

export interface AttendanceRecord {
  id: number
  employee_code: string | null
  employee_name: string | null
  work_date: string
  check_in: string | null
  check_out: string | null
  work_duration_hours: number | string | null
  break_duration_hours: number | string | null
  overtime_hours: number | string | null
  status: string
  missing_hours: number | string
  daily_deduction: number | string
  annotation?: AttendanceAnnotation | null
}

export interface AttendanceIngestResult {
  imported: number
  upserted: number
  skipped: number
  ignored: number
  employees_processed?: number
  errors: string[]
  ignored_records: IgnoredAttendanceRecord[]
  salary_warnings?: string[]
}

export interface IgnoredAttendanceRecord {
  employee_code: string
  employee_name?: string | null
  work_date?: string | null
  reason: string
  status?: string | null
  source?: string | null
}

export interface DailySummary {
  work_date: string
  employees_present: number
  employees_absent: number
  employees_below_min_hours: number
  employees_missing_checkout: number
  total_deductions: number | string
  details: {
    present: AttendanceBrief[]
    absent: AttendanceBrief[]
    below_min_hours: AttendanceBrief[]
    missing_checkout: AttendanceBrief[]
    ignored_records?: IgnoredAttendanceRecord[]
  }
}

export interface AttendanceBrief {
  employee_code: string | null
  employee_name: string | null
  work_duration_hours: number | string | null
  missing_hours: number | string | null
  daily_deduction: number | string | null
  status: string
}

export interface AttendanceStats {
  employee_id: number
  employee_code: string
  employee_name: string
  present_days: number
  absent_days: number
  weekly_offs: number
  leave_days: number
  holidays: number
  total_worked_hours: number | string
  average_daily_hours: number | string
  attendance_percentage: number | string
}

export interface PayrollRecord {
  id: number
  employee_id: number
  year: number
  month: number
  present_days: number
  absent_days: number
  leave_days: number
  weekly_offs: number
  holidays: number
  working_days: number
  total_hours_worked: number | string
  missing_hours: number | string
  salary_deduction: number | string
  final_salary: number | string
  status: string
  employee?: Employee | null
}

export interface ReportGenerateRequest {
  report_type: 'daily_summary' | 'monthly_payroll' | 'attendance_stats'
  format: 'csv' | 'excel' | 'pdf'
  work_date?: string
  year?: number
  month?: number
  start_date?: string
  end_date?: string
}

export interface ReportGenerateResponse {
  path: string
  filename: string
  format: string
  report_type: string
}

export interface NotificationLog {
  id: number
  provider: string
  recipient: string | null
  message: string
  status: string
  error_detail: string | null
}

export interface AiRecommendation {
  id: number
  work_date: string
  employee_id: number | null
  title: string
  reason: string
  recommendation: string
  confidence: 'high' | 'medium' | 'low' | string
  evidence: Record<string, unknown>
  employee?: Employee | null
}

export interface SmartAlert {
  id: number
  work_date: string
  employee_id: number | null
  alert_type: string
  severity: string
  message: string
  evidence: Record<string, unknown>
  status: string
  employee?: Employee | null
}

export interface AiDailyInsight {
  id: number
  work_date: string
  employees_present: number
  employees_absent: number
  employees_below_min_hours: number
  employees_missing_checkout: number
  total_deductions: number | string
  payload: Record<string, unknown>
  recommendations: AiRecommendation[]
}

export interface AiMonthlyInsight {
  id: number
  year: number
  month: number
  company_attendance_percentage: number | string
  average_daily_hours: number | string
  total_salary_deductions: number | string
  payload: Record<string, unknown>
}

export interface ExecutiveSummary {
  id: number
  work_date: string
  summary_text: string
  estimated_deductions: number | string
  payload: Record<string, unknown>
  recommendations: AiRecommendation[]
  alerts: SmartAlert[]
}

export interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    details?: unknown
  }
}

export interface ActivityItem {
  id: string
  type: 'upload' | 'payroll' | 'report' | 'notification' | 'ai'
  title: string
  detail: string
  at: string
}
export interface NotificationSettings {
  id?: number;
  telegram_enabled: boolean;
  telegram_chat_id: string | null;
}