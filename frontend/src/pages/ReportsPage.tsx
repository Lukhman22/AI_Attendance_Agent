import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useForm } from 'react-hook-form'
import { Download, Calendar, BarChart3, Wallet, FileSpreadsheet, FileJson, CheckCircle2, FileText } from 'lucide-react'
import { reportsApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { ReportGenerateResponse } from '../types/api'
import { Button, Card, Input, PageHeader } from '../components/ui'
import { useApp } from '../context/AppContext'
import { monthBounds, todayISO, clsx } from '../utils/format'
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

const REPORT_TYPES = [
  {
    id: 'daily_summary',
    title: 'Daily Summary',
    description: 'A breakdown of today\'s attendance, missing checkouts, and preliminary penalties.',
    icon: Calendar,
    group: 'Daily Operations',
  },
  {
    id: 'attendance_stats',
    title: 'Attendance Stats',
    description: 'Detailed attendance percentages, total working hours, and absent days over a period.',
    icon: BarChart3,
    group: 'Analytics',
  },
  {
    id: 'monthly_payroll',
    title: 'Monthly Payroll',
    description: 'Final payroll calculations including deductions, base salaries, and final payouts.',
    icon: Wallet,
    group: 'Finance',
  },
] as const

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

  const { register, getValues, watch, setValue } = useForm<ReportForm>({
    defaultValues: {
      report_type: 'daily_summary',
      format: 'excel',
      work_date: todayISO(),
      year: bounds.year,
      month: bounds.month,
      start_date: bounds.start,
      end_date: bounds.end,
    },
  })

  const reportType = watch('report_type')
  const format = watch('format')

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 30)))
  }, [history])

  async function downloadReport(filename: string) {
    try {
      const blob = await reportsApi.download(filename)
      if (!blob || blob.size === 0) {
        throw new Error("File received is empty.");
      }
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
    <div className="space-y-10">
      <PageHeader
        title="Reports"
        subtitle="Generate, preview, and download compliance and financial reports in CSV or Excel."
      />

      <div className="grid gap-8 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <section>
            <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Select Report Type</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {REPORT_TYPES.map((type) => {
                const Icon = type.icon
                const isActive = reportType === type.id
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setValue('report_type', type.id)}
                    className={clsx(
                      'group relative flex flex-col items-start rounded-2xl border p-5 text-left transition-all',
                      isActive 
                        ? 'border-brand-500 bg-brand-50/50 shadow-sm ring-1 ring-brand-500 dark:border-brand-500/50 dark:bg-brand-900/10' 
                        : 'border-ink-200 bg-white hover:border-ink-300 hover:bg-ink-50/50 dark:border-ink-800 dark:bg-ink-950 dark:hover:border-ink-700'
                    )}
                  >
                    {isActive && (
                      <div className="absolute right-4 top-4 text-brand-600 dark:text-brand-400">
                        <CheckCircle2 className="h-5 w-5" />
                      </div>
                    )}
                    <div className={clsx(
                      'mb-4 flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                      isActive 
                        ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-400'
                        : 'bg-ink-100 text-ink-600 group-hover:bg-ink-200 dark:bg-ink-800 dark:text-ink-400'
                    )}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400 mb-1">{type.group}</span>
                    <h3 className="font-display text-base font-semibold text-ink-900 dark:text-ink-100">{type.title}</h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-ink-500 dark:text-ink-400 line-clamp-2">{type.description}</p>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="mt-10">
            <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Configuration</h2>
            <Card className="p-6">
              <form className="space-y-6" onSubmit={(e) => {
                e.preventDefault();
                onGenerate(getValues());
              }}>
                <div className="space-y-4">
                  {reportType === 'daily_summary' && (
                    <div>
                      <label className="mb-2 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Target Date</label>
                      <Input type="date" {...register('work_date')} className="max-w-xs" />
                    </div>
                  )}

                  {reportType === 'monthly_payroll' && (
                    <div className="grid grid-cols-2 gap-4 max-w-md">
                      <div>
                        <label className="mb-2 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Year</label>
                        <Input type="number" {...register('year', { valueAsNumber: true })} />
                      </div>
                      <div>
                        <label className="mb-2 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Month (1-12)</label>
                        <Input type="number" min={1} max={12} {...register('month', { valueAsNumber: true })} />
                      </div>
                    </div>
                  )}

                  {reportType === 'attendance_stats' && (
                    <div className="grid grid-cols-2 gap-4 max-w-md">
                      <div>
                        <label className="mb-2 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Start Date</label>
                        <Input type="date" {...register('start_date')} />
                      </div>
                      <div>
                        <label className="mb-2 block text-[13px] font-medium text-ink-700 dark:text-ink-300">End Date</label>
                        <Input type="date" {...register('end_date')} />
                      </div>
                    </div>
                  )}
                  
                  <div className="pt-2">
                    <label className="mb-3 block text-[13px] font-medium text-ink-700 dark:text-ink-300">Export Format</label>
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => setValue('format', 'excel')}
                        className={clsx(
                          'flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors',
                          format === 'excel'
                            ? 'border-emerald-600 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : 'border-ink-200 bg-white text-ink-700 hover:bg-ink-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-300 dark:hover:bg-ink-800'
                        )}
                      >
                        <FileSpreadsheet className="h-4 w-4" /> Excel (.xlsx)
                      </button>
                      <button
                        type="button"
                        onClick={() => setValue('format', 'csv')}
                        className={clsx(
                          'flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors',
                          format === 'csv'
                            ? 'border-brand-600 bg-brand-50 text-brand-800 dark:bg-brand-950/40 dark:text-brand-300'
                            : 'border-ink-200 bg-white text-ink-700 hover:bg-ink-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-300 dark:hover:bg-ink-800'
                        )}
                      >
                        <FileJson className="h-4 w-4" /> CSV Export
                      </button>
                      <button
                        type="button"
                        onClick={() => setValue('format', 'pdf')}
                        className={clsx(
                          'flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors',
                          format === 'pdf'
                            ? 'border-rose-600 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300'
                            : 'border-ink-200 bg-white text-ink-700 hover:bg-ink-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-300 dark:hover:bg-ink-800'
                        )}
                      >
                        <FileText className="h-4 w-4" /> PDF Document
                      </button>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-ink-100 dark:border-ink-800">
                  <Button type="submit" disabled={busy} className="w-full sm:w-auto h-11 px-8 text-[14px]">
                    <Download className="h-4 w-4" /> 
                    {busy ? 'Generating...' : 'Generate & Download Report'}
                  </Button>
                </div>
              </form>
            </Card>
          </section>
        </div>

        <div className="xl:col-span-5">
          <section>
            <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Download History</h2>
            <DataTable
              rows={history.map((item, index) => ({ ...item, _id: `${item.filename}-${index}` }))}
              rowKey={(r) => r._id}
              pageSize={8}
              emptyTitle="No reports generated"
              emptyDescription="Your generated reports will appear here for easy redownloading."
              columns={[
                {
                  key: 'type',
                  header: 'Report',
                  render: (r) => (
                    <div>
                      <p className="font-medium text-ink-900 dark:text-ink-100">{REPORT_TYPES.find(t => t.id === r.report_type)?.title || r.report_type}</p>
                      <p className="text-[11px] uppercase tracking-wider text-ink-500 mt-0.5">{r.format}</p>
                    </div>
                  ),
                },
                {
                  key: 'open',
                  header: '',
                  className: 'text-right',
                  render: (r) => (
                    <button 
                      onClick={() => void downloadReport(r.filename)}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-900 dark:hover:bg-ink-800 dark:hover:text-ink-100"
                      title="Download again"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  ),
                },
              ]}
            />
          </section>
        </div>
      </div>
    </div>
  )
}