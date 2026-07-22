import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, Brain, RefreshCw } from 'lucide-react'
import { aiApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { AiDailyInsight, AiMonthlyInsight, ExecutiveSummary, SmartAlert } from '../types/api'
import { useApp } from '../context/AppContext'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  Skeleton,
  StatCard,
  statusTone,
} from '../components/ui'
import { formatMoney, formatNumber, formatPercent, todayISO } from '../utils/format'
import { AIAssistant } from '../components/AIAssistant'

export function AIInsightsPage() {
  const { insightsRefreshKey } = useApp()
  const [workDate, setWorkDate] = useState(todayISO())
  const dateObj = new Date(workDate || todayISO())
  const year = dateObj.getFullYear()
  const month = dateObj.getMonth() + 1
  const [loading, setLoading] = useState(true)
  const [executive, setExecutive] = useState<ExecutiveSummary | null>(null)
  const [daily, setDaily] = useState<AiDailyInsight | null>(null)
  const [monthly, setMonthly] = useState<AiMonthlyInsight | null>(null)
  const [alerts, setAlerts] = useState<SmartAlert[]>([])

  async function load() {
    setLoading(true)
    try {
      const [execRes, dailyRes, monthlyRes, alertsRes] = await Promise.allSettled([
        aiApi.executiveSummary(workDate),
        aiApi.dailyInsights(workDate),
        aiApi.monthlyInsights(year, month),
        aiApi.alerts({ work_date: workDate }),
      ])
      setExecutive(execRes.status === 'fulfilled' ? execRes.value : null)
      setDaily(dailyRes.status === 'fulfilled' ? dailyRes.value : null)
      setMonthly(monthlyRes.status === 'fulfilled' ? monthlyRes.value : null)
      setAlerts(alertsRes.status === 'fulfilled' ? alertsRes.value : [])
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load AI insights'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [workDate, year, month, insightsRefreshKey])

  const recommendations = executive?.recommendations?.length
    ? executive.recommendations
    : daily?.recommendations || []

  const payrollRows = (monthly?.payload?.payroll_summary as Array<Record<string, unknown>>) || []

  return (
    <div>
      <PageHeader
        title="AI Insights"
        subtitle="Proactive HR analysis for a small team — deterministic, database-backed, and refreshed after uploads."
        actions={
          <Button variant="secondary" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        }
      />

      <Card className="mb-4 grid gap-3 p-4 md:grid-cols-1">
        <div>
          <label className="mb-1 block text-xs text-ink-500">Analysis date</label>
          <Input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} />
        </div>
      </Card>

      <div className="mb-6">
        <AIAssistant context={{ work_date: workDate, year, month }} />
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-64" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Present" value={daily?.employees_present ?? 0} accent="brand" />
            <StatCard label="Absent" value={daily?.employees_absent ?? 0} accent="rose" />
            <StatCard label="Below 8 Hours" value={daily?.employees_below_min_hours ?? 0} accent="amber" />
            <StatCard
              label="Est. Deductions"
              value={formatMoney(executive?.estimated_deductions ?? daily?.total_deductions ?? 0)}
              accent="sky"
            />
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <Card className="p-5">
              <div className="mb-3 flex items-center gap-2">
                <Brain className="h-5 w-5 text-brand-600" />
                <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Executive Summary</h2>
              </div>
              {executive ? (
                <pre className="whitespace-pre-wrap rounded-xl bg-ink-50 p-4 text-sm leading-relaxed dark:bg-ink-900/50">
                  {executive.summary_text}
                </pre>
              ) : (
                <EmptyState
                  title="No executive summary"
                  description="Upload attendance for this date to generate insights automatically."
                />
              )}
            </Card>

            <Card className="p-5">
              <div className="mb-3 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Smart Alerts</h2>
              </div>
              {alerts.length ? (
                <div className="max-h-80 space-y-2 overflow-y-auto">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="rounded-xl border border-ink-100 p-3 text-sm dark:border-ink-800"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Badge tone={statusTone(alert.severity === 'high' ? 'failed' : 'generated')}>
                          {alert.alert_type.replace(/_/g, ' ')}
                        </Badge>
                        <span className="text-xs text-ink-400">{alert.severity}</span>
                      </div>
                      <p className="mt-2">{alert.message}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No alerts" description="Alerts appear after attendance is analyzed." />
              )}
            </Card>
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <Card className="p-5">
              <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Key Findings</h2>
              {recommendations.length ? (
                <div className="mt-4 space-y-3">
                  {recommendations.map((rec) => (
                    <div key={rec.id} className="rounded-xl border border-ink-100 p-4 dark:border-ink-800">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium">{rec.title}</p>
                        <Badge tone={rec.confidence === 'high' ? 'rose' : rec.confidence === 'medium' ? 'amber' : 'slate'}>
                          {rec.confidence}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm">{rec.reason}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No findings" description="No attendance anomalies detected for this date." />
              )}
            </Card>

            <Card className="p-6">
              <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Daily Attendance Insights</h2>
              {daily ? (
                <div className="mt-4 space-y-2 text-sm">
                  <p>Missing checkout: {daily.employees_missing_checkout}</p>
                  <p>
                    Employees needing attention:{' '}
                    {((daily.payload.employees_requiring_attention as string[]) || []).join(', ') || 'None'}
                  </p>
                  <p>
                    Late arrivals: {((daily.payload.late_arrivals as unknown[]) || []).length}
                  </p>
                  <p>
                    Repeated short workdays:{' '}
                    {((daily.payload.repeated_short_workdays as unknown[]) || []).length}
                  </p>
                  <p>
                    Consecutive absences:{' '}
                    {((daily.payload.consecutive_absences as unknown[]) || []).length}
                  </p>
                </div>
              ) : (
                <EmptyState title="No daily insights" description="Upload attendance to analyze this date." />
              )}
            </Card>
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <Card className="p-6">
              <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Monthly Attendance Insights</h2>
              {monthly ? (
                <div className="mt-4 space-y-3 text-sm">
                  <p>Company attendance: {formatPercent(monthly.company_attendance_percentage)}</p>
                  <p>Average daily hours: {formatNumber(monthly.average_daily_hours)}</p>
                  <p>Total deductions: {formatMoney(monthly.total_salary_deductions)}</p>
                  <div>
                    <p className="mb-2 font-medium">Every employee</p>
                    <div className="max-h-56 space-y-2 overflow-y-auto">
                      {((monthly.payload.employees as Array<Record<string, unknown>>) || []).map((emp) => (
                        <div key={String(emp.employee_id)} className="rounded-lg bg-ink-50 p-2 dark:bg-ink-900/40">
                          <p className="font-medium">{String(emp.employee_name)}</p>
                          <p className="text-xs text-ink-500">
                            Attendance {formatPercent(emp.attendance_percentage as number | string)} · Hours{' '}
                            {formatNumber(emp.total_worked_hours as number | string)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState title="No monthly insights" description="Generate attendance for the selected month." />
              )}
            </Card>

            <Card className="p-6">
              <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Payroll Insights</h2>
              {payrollRows.length ? (
                <div className="mt-4 max-h-72 space-y-2 overflow-y-auto text-sm">
                  {payrollRows.map((row, idx) => (
                    <div key={idx} className="rounded-lg border border-ink-100 p-3 dark:border-ink-800">
                      <p className="font-medium">{String(row.employee_name)}</p>
                      <p>
                        Deduction {formatMoney(row.salary_deduction as number | string)} · Final{' '}
                        {formatMoney(row.final_salary as number | string)}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No payroll insights"
                  description="Monthly payroll summary appears after payroll is generated."
                />
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
