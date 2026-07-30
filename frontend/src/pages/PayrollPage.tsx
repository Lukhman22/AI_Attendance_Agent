import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Download, RefreshCw } from 'lucide-react'
import { payrollApi, reportsApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { PayrollRecord } from '../types/api'
import { DataTable } from '../components/DataTable'
import { Button, Input, PageHeader, Skeleton } from '../components/ui'
import { useApp } from '../context/AppContext'
import { formatMoney, formatNumber, monthBounds } from '../utils/format'
import { Link } from 'react-router-dom'
import { X, AlertCircle } from 'lucide-react'

function MissingSalariesModal({ missing, onClose }: { missing: string[], onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-ink-900">
        <div className="mb-4 flex items-center justify-between border-b border-ink-100 pb-4 dark:border-ink-800">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <AlertCircle className="h-5 w-5" />
            <h3 className="text-lg font-semibold">Salaries Not Configured</h3>
          </div>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-700 dark:hover:text-ink-300">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-ink-600 dark:text-ink-300 mb-4">
          Cannot generate payroll because the following employees do not have a monthly salary configured:
        </p>
        <ul className="max-h-60 overflow-y-auto space-y-2 mb-6 border border-ink-200 dark:border-ink-800 rounded-lg p-3 bg-ink-50 dark:bg-ink-950 text-sm">
          {missing.map((emp, i) => (
            <li key={i} className="text-ink-800 dark:text-ink-200 font-medium">{emp}</li>
          ))}
        </ul>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Link to="/payroll/salaries">
            <Button>Go to Employee Salaries</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}

export function PayrollPage() {
  const { pushActivity } = useApp()
  const bounds = monthBounds()
  const [year, setYear] = useState(bounds.year)
  const [month, setMonth] = useState(bounds.month)
  const [rows, setRows] = useState<PayrollRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [missingSalaries, setMissingSalaries] = useState<string[]>([])

  async function load() {
    setLoading(true)
    try {
      const data = await payrollApi.list(year, month)
      setRows(data)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load payroll'))
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [year, month])

  async function generate() {
    setBusy(true)
    try {
      const data = await payrollApi.generate(year, month)
      setRows(data)
      toast.success(`Generated payroll for ${data.length} employees`)
      pushActivity({
        type: 'payroll',
        title: 'Payroll generated',
        detail: `${month}/${year} · ${data.length} employees`,
      })
    } catch (error: any) {
      if (error?.response?.data?.error?.code === 'missing_salary') {
        setMissingSalaries(error.response.data.error.details || [])
      } else {
        toast.error(getErrorMessage(error, 'Payroll generation failed'))
      }
    } finally {
      setBusy(false)
    }
  }

  async function downloadReport(format: 'csv' | 'excel' | 'pdf') {
    setBusy(true)
    try {
      const result = await reportsApi.generate({
        report_type: 'monthly_payroll',
        format,
        year,
        month,
      })
      toast.success(`${format.toUpperCase()} report ready`)
      pushActivity({
        type: 'report',
        title: 'Report created',
        detail: `${result.report_type} (${result.format}) → ${result.path}`,
      })
      // Backend returns server filesystem path; show it for HR to retrieve from reports directory.
      window.prompt('Report saved on server at:', result.path)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Report generation failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {missingSalaries.length > 0 && (
        <MissingSalariesModal missing={missingSalaries} onClose={() => setMissingSalaries([])} />
      )}
      <PageHeader
        title="Payroll"
        subtitle="Generate payroll from uploaded attendance for the selected month. All employees use the configured flat monthly salary."
        actions={
          <>
            <Button variant="secondary" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
            <Button onClick={() => void generate()} disabled={busy}>
              Generate Payroll
            </Button>
          </>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-ink-500">Year</label>
          <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-ink-500">Month</label>
          <Input
            type="number"
            min={1}
            max={12}
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          />
        </div>
        <div className="flex items-end gap-2 sm:col-span-2">
          <Button variant="secondary" disabled={busy} onClick={() => void downloadReport('csv')}>
            <Download className="h-4 w-4" /> CSV
          </Button>
          <Button variant="secondary" disabled={busy} onClick={() => void downloadReport('excel')}>
            <Download className="h-4 w-4" /> Excel
          </Button>
          <Button variant="secondary" disabled={busy} onClick={() => void downloadReport('pdf')}>
            <Download className="h-4 w-4" /> PDF
          </Button>
        </div>
      </div>

      {loading ? (
        <Skeleton className="h-96" />
      ) : (
        <DataTable
          rows={rows}
          rowKey={(r) => r.id}
          emptyTitle="No payroll rows"
          emptyDescription="Generate payroll for the selected month."
          columns={[
            {
              key: 'name',
              header: 'Employee',
              sortable: true,
              sortValue: (r) => r.employee?.name || '',
              render: (r) => r.employee?.name || `Employee #${r.employee_id}`,
            },
            {
              key: 'present',
              header: 'Present Days',
              sortable: true,
              sortValue: (r) => r.present_days,
              render: (r) => r.present_days,
            },
            {
              key: 'leave',
              header: 'Leave Days',
              sortable: true,
              sortValue: (r) => r.leave_days,
              render: (r) => r.leave_days,
            },
            {
              key: 'missing',
              header: 'Missing Hours',
              sortable: true,
              sortValue: (r) => Number(r.missing_hours),
              render: (r) => formatNumber(r.missing_hours),
            },
            {
              key: 'deduction',
              header: 'Deductions',
              sortable: true,
              sortValue: (r) => Number(r.salary_deduction),
              render: (r) => formatMoney(r.salary_deduction),
            },
            {
              key: 'final',
              header: 'Final Salary',
              sortable: true,
              sortValue: (r) => Number(r.final_salary),
              render: (r) => <span className="font-semibold">{formatMoney(r.final_salary)}</span>,
            },
          ]}
        />
      )}
    </div>
  )
}
