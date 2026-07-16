import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Send } from 'lucide-react'
import { attendanceApi, notificationsApi, payrollApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { NotificationLog } from '../types/api'
import { DataTable } from '../components/DataTable'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  PendingBackend,
  Skeleton,
  statusTone,
} from '../components/ui'
import { useApp } from '../context/AppContext'
import { formatMoney, monthBounds, todayISO } from '../utils/format'

export function NotificationsPage() {
  const { pushActivity } = useApp()
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const bounds = monthBounds()

  async function load() {
    setLoading(true)
    try {
      setLogs(await notificationsApi.logs(50))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load notification logs'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function sendMessage(message: string, label: string) {
    setSending(true)
    try {
      await notificationsApi.send(message)
      toast.success(`${label} sent via active provider`)
      pushActivity({
        type: 'notification',
        title: 'Telegram notification sent',
        detail: label,
      })
      await load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Notification send failed'))
    } finally {
      setSending(false)
    }
  }

  async function sendDailySummary() {
    try {
      const summary = await attendanceApi.dailySummary(todayISO())
      const message = [
        `Daily Attendance Summary (${summary.work_date})`,
        `Present: ${summary.employees_present}`,
        `Absent: ${summary.employees_absent}`,
        `Below 8 hours: ${summary.employees_below_min_hours}`,
        `Missing checkout: ${summary.employees_missing_checkout}`,
        `Total deductions: ${formatMoney(summary.total_deductions)}`,
      ].join('\n')
      await sendMessage(message, 'Daily Summary')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not build daily summary'))
    }
  }

  async function sendMonthlyPayroll() {
    try {
      const rows = await payrollApi.list(bounds.year, bounds.month)
      const message = [
        `Monthly Payroll Summary (${bounds.month}/${bounds.year})`,
        `Employees: ${rows.length}`,
        ...rows.slice(0, 15).map(
          (r) =>
            `${r.employee?.name || r.employee_id}: final ${formatMoney(r.final_salary)} (deduction ${formatMoney(r.salary_deduction)})`,
        ),
      ].join('\n')
      await sendMessage(message, 'Monthly Payroll Summary')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not build payroll summary'))
    }
  }

  const latest = logs[0]

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="Send HR summaries through the configured provider and review delivery logs."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Telegram</h2>
          <p className="mt-2 text-sm text-ink-500">
            Active provider is controlled by backend `NOTIFICATION_PROVIDER`.
          </p>
          <div className="mt-4">
            <Badge tone={latest?.provider === 'telegram' ? statusTone(latest.status) : 'slate'}>
              {latest?.provider === 'telegram' ? latest.status : 'Configured via env'}
            </Badge>
          </div>
          <PendingBackend feature="GET provider health/status endpoint" />
        </Card>
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">WhatsApp</h2>
          <p className="mt-2 text-sm text-ink-500">
            Switch backend env to `whatsapp` to route `POST /notifications/send` there.
          </p>
          <div className="mt-4">
            <Badge tone={latest?.provider === 'whatsapp' ? statusTone(latest.status) : 'slate'}>
              {latest?.provider === 'whatsapp' ? latest.status : 'Configured via env'}
            </Badge>
          </div>
          <PendingBackend feature="GET provider health/status endpoint" />
        </Card>
        <Card className="p-5">
          <h2 className="font-display text-lg font-semibold">Quick Send</h2>
          <div className="mt-4 flex flex-col gap-2">
            <Button disabled={sending} onClick={() => void sendDailySummary()}>
              <Send className="h-4 w-4" /> Send Daily Summary
            </Button>
            <Button variant="secondary" disabled={sending} onClick={() => void sendMonthlyPayroll()}>
              <Send className="h-4 w-4" /> Send Monthly Payroll Summary
            </Button>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        {loading ? (
          <Skeleton className="h-80" />
        ) : logs.length ? (
          <DataTable
            rows={logs}
            rowKey={(r) => r.id}
            columns={[
              {
                key: 'provider',
                header: 'Provider',
                sortable: true,
                sortValue: (r) => r.provider,
                render: (r) => r.provider,
              },
              {
                key: 'status',
                header: 'Status',
                render: (r) => <Badge tone={statusTone(r.status)}>{r.status}</Badge>,
              },
              {
                key: 'message',
                header: 'Message',
                render: (r) => <span className="line-clamp-2 max-w-xl text-xs">{r.message}</span>,
              },
              {
                key: 'error',
                header: 'Error',
                render: (r) => r.error_detail || '—',
              },
            ]}
          />
        ) : (
          <EmptyState title="No notification logs" description="Send a summary to create the first log entry." />
        )}
      </div>
    </div>
  )
}
