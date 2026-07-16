import { api } from './apiClient'
import type {
  AiDailyInsight,
  AiMonthlyInsight,
  AttendanceIngestResult,
  AttendanceRecord,
  AttendanceStats,
  DailySummary,
  Employee,
  ExecutiveSummary,
  NotificationLog,
  PayrollRecord,
  ReportGenerateRequest,
  ReportGenerateResponse,
  SmartAlert,
} from '../types/api'

export const attendanceApi = {
  upload: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<AttendanceIngestResult>('/api/v1/attendance/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  dailySummary: async (workDate: string) => {
    const { data } = await api.get<DailySummary>('/api/v1/attendance/daily-summary', {
      params: { work_date: workDate },
    })
    return data
  },
  records: async (workDate: string) => {
    const { data } = await api.get<AttendanceRecord[]>('/api/v1/attendance/records', {
      params: { work_date: workDate },
    })
    return data
  },
  stats: async (startDate: string, endDate: string) => {
    const { data } = await api.get<AttendanceStats[]>('/api/v1/attendance/stats', {
      params: { start_date: startDate, end_date: endDate },
    })
    return data
  },
}

export const employeesApi = {
  list: async () => {
    const { data } = await api.get<Employee[]>('/api/v1/employees')
    return data
  },
  upsert: async (payload: {
    employee_code: string
    name: string
    department?: string | null
    monthly_salary: number
    working_days_per_month: number
  }) => {
    const { data } = await api.post<Employee>('/api/v1/employees', payload)
    return data
  },
  seedRules: async () => {
    const { data } = await api.post('/api/v1/employees/salary-rules/seed')
    return data
  },
}

export const payrollApi = {
  generate: async (year: number, month: number) => {
    const { data } = await api.post<PayrollRecord[]>('/api/v1/payroll/generate', { year, month })
    return data
  },
  list: async (year: number, month: number) => {
    const { data } = await api.get<PayrollRecord[]>(`/api/v1/payroll/${year}/${month}`)
    return data
  },
}

export const reportsApi = {
  generate: async (payload: ReportGenerateRequest) => {
    const { data } = await api.post<ReportGenerateResponse>('/api/v1/reports/generate', payload)
    return data
  },
  download: async (filename: string) => {
    const response = await api.get(`/api/v1/reports/download/${encodeURIComponent(filename)}`, {
      responseType: 'blob',
    })
    return response.data as Blob
  },
}

export const notificationsApi = {
  send: async (message: string) => {
    const { data } = await api.post('/api/v1/notifications/send', { message })
    return data
  },
  logs: async (limit = 50) => {
    const { data } = await api.get<NotificationLog[]>('/api/v1/notifications/logs', {
      params: { limit },
    })
    return data
  },
}

export const aiApi = {
  dailyInsights: async (workDate: string) => {
    const { data } = await api.get<AiDailyInsight>('/api/v1/ai/insights/daily', {
      params: { work_date: workDate },
    })
    return data
  },
  monthlyInsights: async (year: number, month: number) => {
    const { data } = await api.get<AiMonthlyInsight>('/api/v1/ai/insights/monthly', {
      params: { year, month },
    })
    return data
  },
  executiveSummary: async (workDate: string) => {
    const { data } = await api.get<ExecutiveSummary>('/api/v1/ai/executive-summary', {
      params: { work_date: workDate },
    })
    return data
  },
  alerts: async (params: { work_date?: string; year?: number; month?: number }) => {
    const { data } = await api.get<SmartAlert[]>('/api/v1/alerts', { params })
    return data
  },
}

export const systemApi = {
  health: async () => {
    const { data } = await api.get<{ status: string; environment: string }>('/health')
    return data
  },
}
