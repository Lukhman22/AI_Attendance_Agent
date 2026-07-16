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
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Workforce snapshot for ${today}. All metrics are served by the FastAPI middleware.`}
      />

      {(summary?.details?.ignored_records?.length || 0) > 0 ? (
        <Card className="mb-4 border border-amber-300/70 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/40">
          <h2 className="font-display text-base font-semibold text-amber-950 dark:text-amber-100">Warnings</h2>
          <ul className="mt-2 space-y-1 text-sm text-amber-900 dark:text-amber-100">
            {(summary?.details?.ignored_records || []).map((item) => (
              <li key={`${item.employee_code}-${item.work_date || ''}`}>
                Employee ID {item.employee_code} not found — attendance record ignored. Register the employee before re-importing.
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
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

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Attendance Trend</h2>
          <p className="mb-4 text-xs text-ink-500">Attendance % by employee (current month stats API)</p>
          {trendChart.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trendChart}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="attendance" stroke="#227267" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No attendance stats" description="Upload attendance to populate this chart." />
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Department Attendance</h2>
          <p className="mb-4 text-xs text-ink-500">Present vs absent day totals by department</p>
          {departmentChart.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={departmentChart}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="department" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="present" fill="#2d8f80" radius={[6, 6, 0, 0]} />
                <Bar dataKey="absent" fill="#e11d48" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No department data" description="Employee and stats data are required." />
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Average Working Hours</h2>
          <p className="mb-4 text-xs text-ink-500">Backend `average_daily_hours` values</p>
          {hoursChart.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={hoursChart}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(v: number) => formatNumber(v)} />
                <Bar dataKey="hours" fill="#47ab9a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No hours data" description="Generate attendance stats to view averages." />
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Monthly Payroll Distribution</h2>
          <p className="mb-4 text-xs text-ink-500">Final salary vs deductions from payroll API</p>
          {payrollChart.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={payrollChart}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(v: number) => formatMoney(v)} />
                <Legend />
                <Bar dataKey="salary" fill="#227267" radius={[6, 6, 0, 0]} />
                <Bar dataKey="deduction" fill="#f59e0b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No payroll yet" description="Generate payroll for this month to populate chart." />
          )}
        </Card>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Salary Deduction Breakdown</h2>
          <p className="mb-4 text-xs text-ink-500">From today's daily summary details</p>
          {deductionBreakdown.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={deductionBreakdown} dataKey="value" nameKey="name" outerRadius={90} label>
                  {deductionBreakdown.map((_, index) => (
                    <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatMoney(v)} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No deductions today" description="Upload today's attendance to see deduction shares." />
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Recent Activity</h2>
          <div className="mt-4 space-y-3">
            {activity.length ? (
              activity.slice(0, 8).map((item) => (
                <div
                  key={item.id}
                  className="rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2 dark:border-ink-800 dark:bg-ink-900/50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-[11px] text-ink-400">{new Date(item.at).toLocaleString()}</p>
                  </div>
                  <p className="text-xs text-ink-500 dark:text-ink-400">{item.detail}</p>
                </div>
              ))
            ) : (
              <EmptyState
                title="No recent activity"
                description="Uploads, payroll runs, reports, notifications, and AI queries will appear here."
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
