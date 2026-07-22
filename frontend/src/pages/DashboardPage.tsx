import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { attendanceApi, employeesApi, payrollApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { AttendanceStats, DailySummary, Employee, PayrollRecord } from '../types/api'
import { formatMoney, formatNumber, monthBounds, todayISO } from '../utils/format'
import { Card, EmptyState, PageHeader, Skeleton, StatCard } from '../components/ui'
import { useApp } from '../context/AppContext'
import toast from 'react-hot-toast'

const PIE_COLORS = ['#227267', '#47ab9a', '#8195a2', '#f59e0b', '#e11d48']

export function DashboardPage() {
  const { activity } = useApp()
  const [loading, setLoading] = useState(true)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [stats, setStats] = useState<AttendanceStats[]>([])
  const [payroll, setPayroll] = useState<PayrollRecord[]>([])
  const today = todayISO()
  const bounds = monthBounds()

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      try {
        const [emps, daily, monthStats, pay] = await Promise.all([
          employeesApi.list(),
          attendanceApi.dailySummary(today).catch(() => null),
          attendanceApi.stats(bounds.start, bounds.end).catch(() => []),
          payrollApi.list(bounds.year, bounds.month).catch(() => []),
        ])
        if (!mounted) return
        setEmployees(emps)
        setSummary(daily)
        setStats(monthStats)
        setPayroll(pay)
      } catch (error) {
        toast.error(getErrorMessage(error, 'Failed to load dashboard'))
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [bounds.end, bounds.month, bounds.start, bounds.year, today])

  const departmentChart = useMemo(() => {
    const map = new Map<string, { department: string; present: number; absent: number }>()
    for (const emp of employees) {
      const dept = emp.department || 'Unassigned'
      if (!map.has(dept)) map.set(dept, { department: dept, present: 0, absent: 0 })
    }
    for (const row of stats) {
      const emp = employees.find((e) => e.id === row.employee_id)
      const dept = emp?.department || 'Unassigned'
      const bucket = map.get(dept) || { department: dept, present: 0, absent: 0 }
      bucket.present += row.present_days
      bucket.absent += row.absent_days
      map.set(dept, bucket)
    }
    return [...map.values()]
  }, [employees, stats])

  const hoursChart = useMemo(
    () =>
      stats.map((s) => ({
        name: s.employee_name.split(' ')[0],
        hours: Number(s.average_daily_hours),
      })),
    [stats],
  )

  const payrollChart = useMemo(
    () =>
      payroll.map((p) => ({
        name: p.employee?.name?.split(' ')[0] || `Emp ${p.employee_id}`,
        salary: Number(p.final_salary),
        deduction: Number(p.salary_deduction),
      })),
    [payroll],
  )

  const trendChart = useMemo(() => {
    // Visualize backend attendance percentage distribution for the month (no client recalculation).
    return stats.map((s) => ({
      name: s.employee_name.split(' ')[0],
      attendance: Number(s.attendance_percentage),
    }))
  }, [stats])

  const deductionBreakdown = useMemo(
    () =>
      (summary?.details.below_min_hours || [])
        .concat(summary?.details.absent || [])
        .map((row) => ({
          name: row.employee_name || row.employee_code || 'Employee',
          value: Number(row.daily_deduction || 0),
        }))
        .filter((row) => row.value > 0),
    [summary],
  )

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-12 w-64" />
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-6 xl:grid-cols-2">
          <Skeleton className="h-96 rounded-xl xl:col-span-2" />
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <PageHeader
        title="Executive Overview"
        subtitle={`Workforce snapshot for ${today}. All metrics are served by the FastAPI middleware.`}
      />

      {(summary?.details?.ignored_records?.length || 0) > 0 ? (
        <Card className="border border-amber-300/70 bg-amber-50 p-5 dark:border-amber-800 dark:bg-amber-950/40">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-200/50 text-amber-700 dark:bg-amber-900/50 dark:text-amber-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="font-display text-sm font-semibold text-amber-950 dark:text-amber-100">Action Required: Unregistered Employees</h2>
          </div>
          <ul className="mt-3 ml-11 list-disc space-y-1 text-sm text-amber-900 dark:text-amber-200">
            {(summary?.details?.ignored_records || []).map((item) => (
              <li key={`${item.employee_code}-${item.work_date || ''}`}>
                Employee ID <strong>{item.employee_code}</strong> not found. Register them before re-importing.
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {/* Snapshot Section */}
      <section>
        <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Today's Snapshot</h2>
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Total Employees" value={employees.length} accent="slate" />
          <StatCard label="Present Today" value={summary?.employees_present ?? 0} accent="brand" />
          <StatCard label="Absent Today" value={summary?.employees_absent ?? 0} accent="rose" />
          <StatCard
            label="Below 8 Hours"
            value={summary?.employees_below_min_hours ?? 0}
            accent="amber"
          />
          <StatCard
            label="Today's Deductions"
            value={formatMoney(summary?.total_deductions ?? 0)}
            accent="sky"
          />
        </div>
      </section>

      {/* Attendance Overview */}
      <section>
        <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Attendance Overview</h2>
        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="flex flex-col p-6 xl:col-span-2">
            <div className="mb-6">
              <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Monthly Attendance Trend</h3>
              <p className="mt-1 text-sm text-ink-500">Individual attendance percentages for the current month</p>
            </div>
            <div className="min-h-[320px] flex-1">
              {trendChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendChart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dy={10} />
                    <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dx={-10} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }} />
                    <Line type="monotone" dataKey="attendance" stroke="#227267" strokeWidth={3} dot={{ r: 4, fill: '#227267', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No attendance stats" description="Upload attendance to populate this chart." />
              )}
            </div>
          </Card>

          <Card className="flex flex-col p-6">
            <div className="mb-6">
              <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Department Distribution</h3>
              <p className="mt-1 text-sm text-ink-500">Present vs absent days by department</p>
            </div>
            <div className="min-h-[280px] flex-1">
              {departmentChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={departmentChart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="department" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dx={-10} />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                    <Bar dataKey="present" fill="#2d8f80" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    <Bar dataKey="absent" fill="#e11d48" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No department data" description="Employee and stats data are required." />
              )}
            </div>
          </Card>

          <Card className="flex flex-col p-6">
            <div className="mb-6">
              <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Average Working Hours</h3>
              <p className="mt-1 text-sm text-ink-500">Daily averages based on backend calculations</p>
            </div>
            <div className="min-h-[280px] flex-1">
              {hoursChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hoursChart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dx={-10} />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} formatter={(v: number) => formatNumber(v)} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Bar dataKey="hours" fill="#47ab9a" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No hours data" description="Generate attendance stats to view averages." />
              )}
            </div>
          </Card>
        </div>
      </section>

      {/* Payroll Overview */}
      <section>
        <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Payroll Overview</h2>
        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="flex flex-col p-6">
            <div className="mb-6">
              <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Salary vs Deductions</h3>
              <p className="mt-1 text-sm text-ink-500">Current month payroll distribution</p>
            </div>
            <div className="min-h-[280px] flex-1">
              {payrollChart.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={payrollChart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8195a2' }} dx={-10} />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} formatter={(v: number) => formatMoney(v)} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                    <Bar dataKey="salary" fill="#227267" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    <Bar dataKey="deduction" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No payroll yet" description="Generate payroll for this month to populate chart." />
              )}
            </div>
          </Card>

          <Card className="flex flex-col p-6">
            <div className="mb-6">
              <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Today's Deductions</h3>
              <p className="mt-1 text-sm text-ink-500">Breakdown of penalties applied today</p>
            </div>
            <div className="min-h-[280px] flex-1">
              {deductionBreakdown.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={deductionBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2}>
                      {deductionBreakdown.map((_, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => formatMoney(v)} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No deductions today" description="Upload today's attendance to see deduction shares." />
              )}
            </div>
          </Card>
        </div>
      </section>

      {/* Employee Insights & Activity */}
      <section>
        <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Employee Insights & Activity</h2>
        <Card className="p-0">
          <div className="border-b border-ink-100 px-6 py-5 dark:border-ink-800">
            <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-50">Recent System Activity</h3>
            <p className="mt-1 text-sm text-ink-500">Latest actions across the platform</p>
          </div>
          <div className="flex flex-col divide-y divide-ink-100 dark:divide-ink-800/50">
            {activity.length ? (
              activity.slice(0, 5).map((item) => (
                <div key={item.id} className="flex items-start justify-between gap-4 px-6 py-4 transition-colors hover:bg-ink-50/50 dark:hover:bg-ink-900/30">
                  <div>
                    <p className="text-sm font-medium text-ink-900 dark:text-ink-100">{item.title}</p>
                    <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">{item.detail}</p>
                  </div>
                  <span className="shrink-0 text-xs text-ink-400 dark:text-ink-500">{new Date(item.at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
                </div>
              ))
            ) : (
              <div className="px-6 py-10">
                <EmptyState title="No recent activity" description="Uploads, payroll runs, reports, and API queries will appear here." />
              </div>
            )}
          </div>
        </Card>
      </section>
    </div>
  )
}
