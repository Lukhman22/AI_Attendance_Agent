import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, Upload } from 'lucide-react'
import { attendanceApi, employeesApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { AttendanceRecord, DailySummary, Employee, IgnoredAttendanceRecord } from '../types/api'
import { DataTable } from '../components/DataTable'
import { Badge, Button, Card, Input, PageHeader, Select, Skeleton, statusTone } from '../components/ui'
import { useApp } from '../context/AppContext'
import { formatNumber, todayISO } from '../utils/format'

export function AttendancePage() {
  const { pushActivity, bumpInsightsRefresh } = useApp()
  const [date, setDate] = useState(todayISO())
  const [department, setDepartment] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [rows, setRows] = useState<AttendanceRecord[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadWarnings, setUploadWarnings] = useState<IgnoredAttendanceRecord[]>([])
  const [summaryIgnored, setSummaryIgnored] = useState<IgnoredAttendanceRecord[]>([])

  const employeeDept = useMemo(() => {
    const map = new Map<string, string>()
    for (const emp of employees) {
      map.set(emp.employee_code, emp.department || 'Unassigned')
    }
    return map
  }, [employees])

  async function load(workDate = date) {
    setLoading(true)
    try {
      const [records, emps, summary] = await Promise.all([
        attendanceApi.records(workDate),
        employeesApi.list(),
        attendanceApi.dailySummary(workDate).catch(() => null as DailySummary | null),
      ])
      setRows(records)
      setEmployees(emps)
      setSummaryIgnored(summary?.details?.ignored_records || [])
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load attendance records'))
      setRows([])
      setSummaryIgnored([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load(date)
  }, [date])

  const departmentOptions = useMemo(() => {
    return [...new Set(employees.map((e) => e.department || 'Unassigned'))].sort()
  }, [employees])

  const enriched = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        department: row.employee_code ? employeeDept.get(row.employee_code) || 'Unassigned' : 'Unassigned',
      })),
    [employeeDept, rows],
  )

  const filtered = useMemo(() => {
    return enriched.filter((row) => {
      const matchesStatus = status === 'all' || row.status === status
      const matchesDept = department === 'all' || row.department === department
      const hay = `${row.employee_code ?? ''} ${row.employee_name ?? ''} ${row.department}`.toLowerCase()
      const matchesSearch = !search || hay.includes(search.toLowerCase())
      return matchesStatus && matchesSearch && matchesDept
    })
  }, [department, enriched, search, status])

  const warningRows = uploadWarnings.length ? uploadWarnings : summaryIgnored

  async function onUpload(file?: File | null) {
    if (!file) return
    setUploading(true)
    try {
      const result = await attendanceApi.upload(file)
      const ignored = result.ignored_records || []
      setUploadWarnings(ignored)
      const processed = result.imported + result.upserted
      const employees = result.employees_processed ?? processed
      toast.success(
        `Attendance Upload Completed — Employees: ${employees}, Records: ${processed}, Ignored: ${result.ignored ?? 0}`,
      )
      pushActivity({
        type: 'upload',
        title: 'Attendance uploaded',
        detail: `${file.name}: employees ${employees}, records ${processed}, ignored ${result.ignored ?? 0}`,
      })
      if (result.salary_warnings?.length) {
        toast.error(`${result.salary_warnings.length} salary warning(s) — set salaries in Employees or the directory file`)
      }
      if (result.errors?.length) toast.error(`${result.errors.length} row warning(s)`)
      bumpInsightsRefresh()
      await load(date)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Upload failed'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Attendance"
        subtitle="Upload biometric CSV/Excel exports and review normalized records from the API."
        actions={
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              accept=".csv,.xlsx,.xlsm,.xls"
              className="hidden"
              disabled={uploading}
              onChange={(e) => void onUpload(e.target.files?.[0])}
            />
            <span className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700">
              <Upload className="h-4 w-4" />
              {uploading ? 'Uploading…' : 'Upload CSV / Excel'}
            </span>
          </label>
        }
      />

      {warningRows.length ? (
        <Card className="mb-4 border border-amber-300/80 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/30">
          <div className="mb-2 flex items-center gap-2 text-amber-900 dark:text-amber-100">
            <AlertTriangle className="h-4 w-4" />
            <h2 className="font-display text-base font-semibold">Warnings</h2>
          </div>
          <ul className="space-y-2 text-sm text-amber-950 dark:text-amber-50">
            {warningRows.map((item) => (
              <li key={`${item.employee_code}-${item.work_date || ''}`}>
                <p className="font-medium">Employee ID {item.employee_code} not found.</p>
                <p className="text-amber-800 dark:text-amber-200">
                  Attendance record ignored. Please register this employee before importing attendance.
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-300">{item.reason}</p>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card className="mb-4 grid gap-3 p-4 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-500">Date</label>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-500">Status</label>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All statuses</option>
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="leave">Leave</option>
            <option value="missing_checkout">Missing checkout</option>
            <option value="weekly_off">Weekly off</option>
            <option value="holiday">Holiday</option>
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-500">Department</label>
          <Select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="all">All departments</option>
            {departmentOptions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-500">Search</label>
          <Input
            placeholder="Employee ID or name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </Card>

      {loading ? (
        <Skeleton className="h-96" />
      ) : (
        <DataTable
          rows={filtered}
          rowKey={(r) => r.id}
          emptyTitle="No attendance records"
          emptyDescription="Upload a biometric export or choose another date."
          columns={[
            {
              key: 'code',
              header: 'Employee ID',
              sortable: true,
              sortValue: (r) => r.employee_code || '',
              render: (r) => <span className="font-mono text-xs">{r.employee_code}</span>,
            },
            {
              key: 'name',
              header: 'Name',
              sortable: true,
              sortValue: (r) => r.employee_name || '',
              render: (r) => r.employee_name,
            },
            {
              key: 'department',
              header: 'Department',
              sortable: true,
              sortValue: (r) => r.department,
              render: (r) => r.department,
            },
            {
              key: 'in',
              header: 'Check In',
              render: (r) => r.check_in || '—',
            },
            {
              key: 'out',
              header: 'Check Out',
              render: (r) => r.check_out || '—',
            },
            {
              key: 'hours',
              header: 'Work Hours',
              sortable: true,
              sortValue: (r) => Number(r.work_duration_hours || 0),
              render: (r) => formatNumber(r.work_duration_hours),
            },
            {
              key: 'break',
              header: 'Break Hours',
              render: (r) => formatNumber(r.break_duration_hours),
            },
            {
              key: 'status',
              header: 'Status',
              sortable: true,
              sortValue: (r) => r.status,
              render: (r) => <Badge tone={statusTone(r.status)}>{r.status.replace(/_/g, ' ')}</Badge>,
            },
          ]}
        />
      )}

      <div className="mt-4 flex justify-end">
        <Button variant="secondary" onClick={() => void load(date)}>
          Refresh
        </Button>
      </div>
    </div>
  )
}
