import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { useForm } from 'react-hook-form'
import { attendanceApi, employeesApi, payrollApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { AttendanceStats, Employee, PayrollRecord } from '../types/api'
import { DataTable } from '../components/DataTable'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  PendingBackend,
  Skeleton,
} from '../components/ui'
import { formatMoney, formatNumber, formatPercent, monthBounds } from '../utils/format'

interface EmployeeForm {
  employee_code: string
  name: string
  department: string
  monthly_salary: number
  working_days_per_month: number
}

export function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [stats, setStats] = useState<AttendanceStats[]>([])
  const [payroll, setPayroll] = useState<PayrollRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Employee | null>(null)
  const bounds = monthBounds()
  const { register, handleSubmit, reset } = useForm<EmployeeForm>({
    defaultValues: {
      working_days_per_month: 26,
      monthly_salary: 0,
    },
  })

  async function load() {
    setLoading(true)
    try {
      const [emps, monthStats, pay] = await Promise.all([
        employeesApi.list(),
        attendanceApi.stats(bounds.start, bounds.end).catch(() => []),
        payrollApi.list(bounds.year, bounds.month).catch(() => []),
      ])
      setEmployees(emps)
      setStats(monthStats)
      setPayroll(pay)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load employees'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const statsMap = useMemo(() => {
    const map = new Map<number, AttendanceStats>()
    for (const row of stats) map.set(row.employee_id, row)
    return map
  }, [stats])

  const rows = useMemo(() => {
    return employees
      .filter((e) => {
        const hay = `${e.employee_code} ${e.name} ${e.department ?? ''}`.toLowerCase()
        return !search || hay.includes(search.toLowerCase())
      })
      .map((e) => ({
        ...e,
        attendance_percentage: statsMap.get(e.id)?.attendance_percentage ?? 0,
        leave_days: statsMap.get(e.id)?.leave_days ?? 0,
        average_daily_hours: statsMap.get(e.id)?.average_daily_hours ?? 0,
      }))
  }, [employees, search, statsMap])

  const employeePayroll = useMemo(
    () => payroll.filter((p) => selected && p.employee_id === selected.id),
    [payroll, selected],
  )

  const selectedStats = selected ? statsMap.get(selected.id) : undefined

  async function onCreate(values: EmployeeForm) {
    try {
      await employeesApi.upsert({
        ...values,
        department: values.department || null,
        monthly_salary: Number(values.monthly_salary),
        working_days_per_month: Number(values.working_days_per_month),
      })
      toast.success('Employee saved')
      reset({ working_days_per_month: 26, monthly_salary: 0, employee_code: '', name: '', department: '' })
      await load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save employee'))
    }
  }

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="Employee master data and current-month attendance metrics from the API."
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Input
          className="max-w-md"
          placeholder="Search employees"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <Skeleton className="h-96" />
      ) : (
        <DataTable
          rows={rows}
          rowKey={(r) => r.id}
          emptyTitle="No employees"
          emptyDescription="Register employees here before uploading attendance."
          columns={[
            {
              key: 'code',
              header: 'Employee ID',
              sortable: true,
              sortValue: (r) => r.employee_code,
              render: (r) => <span className="font-mono text-xs">{r.employee_code}</span>,
            },
            {
              key: 'name',
              header: 'Name',
              sortable: true,
              sortValue: (r) => r.name,
              render: (r) => (
                <button className="font-medium text-brand-700 hover:underline dark:text-brand-300" onClick={() => setSelected(r)}>
                  {r.name}
                </button>
              ),
            },
            {
              key: 'dept',
              header: 'Department',
              sortable: true,
              sortValue: (r) => r.department || '',
              render: (r) => r.department || '—',
            },
            {
              key: 'salary',
              header: 'Monthly Salary',
              sortable: true,
              sortValue: (r) => Number(r.monthly_salary),
              render: (r) => formatMoney(r.monthly_salary),
            },
            {
              key: 'attn',
              header: 'Attendance %',
              sortable: true,
              sortValue: (r) => Number(r.attendance_percentage),
              render: (r) => formatPercent(r.attendance_percentage),
            },
          ]}
        />
      )}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Add / Update Employee</h2>
          <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={handleSubmit(onCreate)}>
            <Input placeholder="Employee ID" {...register('employee_code', { required: true })} />
            <Input placeholder="Full name" {...register('name', { required: true })} />
            <Input placeholder="Department" {...register('department')} />
            <Input
              type="number"
              step="0.01"
              placeholder="Monthly salary"
              {...register('monthly_salary', { required: true, valueAsNumber: true })}
            />
            <Input
              type="number"
              placeholder="Working days / month"
              {...register('working_days_per_month', { required: true, valueAsNumber: true })}
            />
            <Button type="submit">Save Employee</Button>
          </form>
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Employee Profile</h2>
          {!selected ? (
            <EmptyState title="Select an employee" description="Click a name in the table to open the profile panel." />
          ) : (
            <div className="mt-4 space-y-4">
              <div>
                <p className="font-display text-xl font-semibold">{selected.name}</p>
                <p className="text-sm text-ink-500">
                  {selected.employee_code} · {selected.department || 'Unassigned'}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl bg-ink-50 p-3 dark:bg-ink-900/50">
                  <p className="text-xs text-ink-500">Attendance %</p>
                  <p className="text-lg font-semibold">{formatPercent(selectedStats?.attendance_percentage)}</p>
                </div>
                <div className="rounded-xl bg-ink-50 p-3 dark:bg-ink-900/50">
                  <p className="text-xs text-ink-500">Avg Daily Hours</p>
                  <p className="text-lg font-semibold">{formatNumber(selectedStats?.average_daily_hours)}</p>
                </div>
                <div className="rounded-xl bg-ink-50 p-3 dark:bg-ink-900/50">
                  <p className="text-xs text-ink-500">Leave Days (month)</p>
                  <p className="text-lg font-semibold">{selectedStats?.leave_days ?? 0}</p>
                </div>
                <div className="rounded-xl bg-ink-50 p-3 dark:bg-ink-900/50">
                  <p className="text-xs text-ink-500">Absent Days</p>
                  <p className="text-lg font-semibold">{selectedStats?.absent_days ?? 0}</p>
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium">Payroll history (current month API)</p>
                {employeePayroll.length ? (
                  employeePayroll.map((p) => (
                    <div key={p.id} className="mb-2 rounded-xl border border-ink-100 p-3 text-sm dark:border-ink-800">
                      <div className="flex items-center justify-between">
                        <span>
                          {p.month}/{p.year}
                        </span>
                        <Badge>{p.status}</Badge>
                      </div>
                      <p>Present: {p.present_days} · Leave: {p.leave_days}</p>
                      <p>Missing hours: {formatNumber(p.missing_hours)}</p>
                      <p>Deduction: {formatMoney(p.salary_deduction)}</p>
                      <p className="font-medium">Final: {formatMoney(p.final_salary)}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-ink-500">No payroll rows for this employee in the selected month.</p>
                )}
              </div>

              <PendingBackend feature="paginated per-employee attendance day history endpoint" />
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
