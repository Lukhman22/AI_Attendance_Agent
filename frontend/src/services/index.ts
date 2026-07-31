import axios from 'axios'
import { api } from './apiClient'
import type {
  AiDailyInsight,
  AiMonthlyInsight,
  AttendanceIngestResult,
  AttendanceRecord,
  AttendanceAnnotation,
  AttendanceStats,
  DailySummary,
  Employee,
  ExecutiveSummary,
  NotificationLog,
  NotificationSettings,
  PayrollRecord,
  ReportGenerateRequest,
  ReportGenerateResponse,
  SmartAlert,
} from '../types/api'

export const attendanceApi = {
  upload: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<AttendanceIngestResult>('/attendance/upload', form)
    return data
  },
  dailySummary: async (workDate: string) => {
    const { data } = await api.get<DailySummary>('/attendance/daily-summary', {
      params: { work_date: workDate },
    })
    return data
  },
  records: async (workDate: string) => {
    const { data } = await api.get<AttendanceRecord[]>('/attendance/records', {
      params: { work_date: workDate },
    })
    return Array.isArray(data) ? data : []
  },
  stats: async (startDate: string, endDate: string) => {
    const { data } = await api.get<AttendanceStats[]>('/attendance/stats', {
      params: { start_date: startDate, end_date: endDate },
    })
    return Array.isArray(data) ? data : []
  },
}

export const annotationsApi = {
  list: async (workDate?: string, startDate?: string, endDate?: string) => {
    const { data } = await api.get<AttendanceAnnotation[]>('/annotations', {
      params: { work_date: workDate, start_date: startDate, end_date: endDate },
    })
    return Array.isArray(data) ? data : []
  },
  upsert: async (employeeId: number, workDate: string, annotationType: string, notes?: string) => {
    const { data } = await api.put<AttendanceAnnotation>(`/annotations/${employeeId}/${workDate}`, {
      annotation_type: annotationType,
      notes,
    })
    return data
  },
  delete: async (annotationId: number) => {
    const { data } = await api.delete(`/annotations/${annotationId}`)
    return data
  },
}

export const employeesApi = {
  list: async () => {
    const { data } = await api.get<Employee[]>('/employees')
    return Array.isArray(data) ? data : []
  },
  upsert: async (payload: {
    employee_code: string
    name: string
    department?: string | null
    working_days_per_month: number
  }) => {
    const { data } = await api.post<Employee>('/employees', payload)
    return data
  },
  seedRules: async () => {
    const { data } = await api.post('/employees/salary-rules/seed')
    return data
  },
}

export const payrollApi = {
  generate: async (year: number, month: number) => {
    const { data } = await api.post<PayrollRecord[]>('/payroll/generate', { year, month })
    return Array.isArray(data) ? data : []
  },
  list: async (year: number, month: number) => {
    const { data } = await api.get<PayrollRecord[]>(`/payroll/${year}/${month}`)
    return Array.isArray(data) ? data : []
  },
}

export const reportsApi = {
  generate: async (payload: ReportGenerateRequest) => {
    const { data } = await api.post<ReportGenerateResponse>('/reports/generate', payload)
    return data
  },
  download: async (filename: string) => {
    const response = await api.get(`/reports/download/${encodeURIComponent(filename)}`, {
      responseType: 'blob',
    })
    return response.data as Blob
  },
}

export const notificationsApi = {
  send: async (message: string) => {
    const { data } = await api.post('/notifications/send', { message })
    return data
  },
  logs: async (limit = 50) => {
    const { data } = await api.get<NotificationLog[]>('/notifications/logs', {
      params: { limit },
    })
    return Array.isArray(data) ? data : []
  },
  getSettings: async () => {
    const { data } = await api.get<NotificationSettings>('/notifications/settings')
    return data
  },
  updateSettings: async (settings: NotificationSettings) => {
    const { data } = await api.put<NotificationSettings>('/notifications/settings', settings)
    return data
  },
  triggerDailySummary: async (date?: string) => {
    const { data } = await api.post('/notifications/trigger/daily-summary', null, {
      params: { date },
    })
    return data
  },
  triggerMonthlySummary: async (month: number, year: number) => {
    const { data } = await api.post('/notifications/trigger/monthly-summary', null, {
      params: { month, year },
    })
    return data
  },
}

export const aiApi = {
  dailyInsights: async (workDate: string) => {
    const { data } = await api.get<AiDailyInsight>('/ai/insights/daily', {
      params: { work_date: workDate },
    })
    return data
  },
  monthlyInsights: async (year: number, month: number) => {
    const { data } = await api.get<AiMonthlyInsight>('/ai/insights/monthly', {
      params: { year, month },
    })
    return data
  },
  executiveSummary: async (workDate: string) => {
    const { data } = await api.get<ExecutiveSummary>('/ai/executive-summary', {
      params: { work_date: workDate },
    })
    return data
  },
  alerts: async (params: { work_date?: string; year?: number; month?: number }) => {
    const { data } = await api.get<SmartAlert[]>('/alerts', { params })
    return Array.isArray(data) ? data : []
  },
  ask: async (question: string, context?: { work_date?: string; year?: number; month?: number, employee_id?: number, compare_employee_id?: number, intent?: string, granularity?: string }) => {
    const { data } = await api.post<{ question: string; answer: string; references: Record<string, any>, context?: any }>('/ai/ask', { question, context })
    return data
  },
  transcribe: async (audioBlob: Blob) => {
    const formData = new FormData()
    formData.append('audio', audioBlob)
    const { data } = await api.post<{ text: string }>('/ai/transcribe', formData)
    return data
  },
}

export const systemApi = {
  health: async () => {
    const { data } = await axios.get<{ status: string; environment: string }>('/health')
    return data
  },
}

export interface EmployeeSalary {
  id: number
  employee_id: string
  employee_name: string | null
  monthly_salary: number
  effective_from: string | null
}

export const salariesApi = {
  list: async () => {
    const { data } = await api.get<EmployeeSalary[]>('/salaries')
    return Array.isArray(data) ? data : []
  },
  create: async (payload: { employee_id: string; employee_name: string; monthly_salary: number }) => {
    const { data } = await api.post<EmployeeSalary>('/salaries', payload)
    return data
  },
  update: async (id: number, payload: { monthly_salary: number }) => {
    const { data } = await api.put<EmployeeSalary>(`/salaries/${id}`, payload)
    return data
  },
  bulkUpdate: async (payload: { id: number, employee_id: string, employee_name: string, monthly_salary: number }[]) => {
    const { data } = await api.put<{ message: string }>('/salaries/bulk', payload)
    return data
  },
  delete: async (id: number) => {
    const { data } = await api.delete<{ message: string }>(`/salaries/${id}`)
    return data
  },
  previewImport: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<{
      new_employees: any[]
      existing_to_update: any[]
      invalid_rows: any[]
      duplicates: any[]
    }>('/salaries/import/preview', form)
    return data
  },
  confirmImport: async (payload: any) => {
    const { data } = await api.post<{ message: string }>('/salaries/import/confirm', payload)
    return data
  },
}
