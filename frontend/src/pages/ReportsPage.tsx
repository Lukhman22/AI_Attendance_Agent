import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useForm } from 'react-hook-form'
import { Download, FileText } from 'lucide-react'
import { reportsApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { ReportGenerateResponse } from '../types/api'
import { Button, Card, Input, PageHeader, Select } from '../components/ui'
import { useApp } from '../context/AppContext'
import { monthBounds, todayISO } from '../utils/format'
import { DataTable } from '../components/DataTable'

interface ReportForm {
  report_type: 'daily_summary' | 'monthly_payroll' | 'attendance_stats'
  format: 'csv' | 'excel' | 'pdf'
  work_date: string
  year: number
  month: number
  start_date: string
  end_date: string
}

const HISTORY_KEY = 'hr_report_history'

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function ReportsPage() {
  const { pushActivity } = useApp()
  const bounds = monthBounds()
  const [busy, setBusy] = useState(false)
  const [history, setHistory] = useState<ReportGenerateResponse[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as ReportGenerateResponse[]
    } catch {
      return []
    }
  })

  const { register, handleSubmit, watch } = useForm<ReportForm>({
    defaultValues: {
      report_type: 'daily_summary',
      format: 'csv',
      work_date: todayISO(),
      year: bounds.year,
      month: bounds.month,
      start_date: bounds.start,
      end_date: bounds.end,
    },
  })

  const reportType = watch('report_type')

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 30)))
  }, [history])

  async function downloadReport(filename: string) {
    try {
      const blob = await reportsApi.download(filename)
      triggerBrowserDownload(blob, filename)
      toast.success(`Downloaded ${filename}`)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Download failed'))
    }
  }

  async function onGenerate(values: ReportForm) {
    setBusy(true)
    try {
      const payload = {
        report_type: values.report_type,
        format: values.format,
        work_date: values.report_type === 'daily_summary' ? values.work_date : undefined,
        year: values.report_type === 'monthly_payroll' ? Number(values.year) : undefined,
        month: values.report_type === 'monthly_payroll' ? Number(values.month) : undefined,
        start_date: values.report_type === 'attendance_stats' ? values.start_date : undefined,
        end_date: values.report_type === 'attendance_stats' ? values.end_date : undefined,
      }
      const result = await reportsApi.generate(payload)
      setHistory((prev) => [result, ...prev].slice(0, 30))
      pushActivity({
        type: 'report',
        title: 'Report created',
        detail: `${result.report_type} · ${result.format} · ${result.filename}`,
      })
      await downloadReport(result.filename)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to generate report'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Generate and download attendance and payroll reports in CSV, Excel, or PDF."
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Generate Report</h2>
          <form className="mt-4 space-y-3" onSubmit={handleSubmit(onGenerate)}>
            <div>
              <label className="mb-1 block text-xs text-ink-500">Report type</label>
              <Select {...register('report_type')}>
                <option value="daily_summary">Daily Summary</option>
                <option value="monthly_payroll">Monthly Payroll</option>
                <option value="attendance_stats">Attendance Stats</option>
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-ink-500">Format</label>
              <Select {...register('format')}>
                <option value="csv">CSV</option>
                <option value="excel">Excel</option>
                <option value="pdf">PDF</option>
              </Select>
            </div>

            {reportType === 'daily_summary' ? (
              <div>
                <label className="mb-1 block text-xs text-ink-500">Work date</label>
                <Input type="date" {...register('work_date', { required: true })} />
              </div>
            ) : null}

            {reportType === 'monthly_payroll' ? (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-ink-500">Year</label>
                  <Input type="number" {...register('year', { valueAsNumber: true })} />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-ink-500">Month</label>
                  <Input type="number" min={1} max={12} {...register('month', { valueAsNumber: true })} />
                </div>
              </div>
            ) : null}

            {reportType === 'attendance_stats' ? (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-ink-500">Start date</label>
                  <Input type="date" {...register('start_date')} />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-ink-500">End date</label>
                  <Input type="date" {...register('end_date')} />
                </div>
              </div>
            ) : null}

            <div className="pt-2">
              <Button type="submit" disabled={busy}>
                <FileText className="h-4 w-4" /> Generate & Download
              </Button>
            </div>
          </form>
        </Card>

        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Previously Generated</h2>
          <p className="mb-4 text-xs text-ink-500">Reports generated in this browser session.</p>
          <DataTable
            rows={history.map((item, index) => ({ ...item, _id: `${item.filename}-${index}` }))}
            rowKey={(r) => r._id}
            emptyTitle="No reports yet"
            emptyDescription="Generate a report to see it listed here."
            columns={[
              {
                key: 'type',
                header: 'Type',
                render: (r) => r.report_type,
              },
              {
                key: 'format',
                header: 'Format',
                render: (r) => r.format.toUpperCase(),
              },
              {
                key: 'filename',
                header: 'File',
                render: (r) => <span className="font-mono text-[11px]">{r.filename}</span>,
              },
              {
                key: 'open',
                header: '',
                render: (r) => (
                  <Button variant="secondary" onClick={() => void downloadReport(r.filename)}>
                    <Download className="h-4 w-4" /> Download
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      </div>
    </div>
  )
}
