import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Send } from 'lucide-react'
import { notificationsApi } from '../services' // Now handles logs AND triggers!
import { getErrorMessage } from '../services/apiClient'
import type { NotificationLog } from '../types/api'
import { DataTable } from '../components/DataTable'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Skeleton,
  StatCard,
  Modal,
  Input,
  Select,
} from '../components/ui'
import { useApp } from '../context/AppContext'
import { todayISO } from '../utils/format'

export function NotificationsPage() {
  const { pushActivity } = useApp()
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  
  const [selectedDate, setSelectedDate] = useState(todayISO())
  const [selectedLog, setSelectedLog] = useState<NotificationLog | null>(null)
  
  // Search and Filter states
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  async function load() {
    setLoading(true)
    try {
      setLogs(await notificationsApi.logs(100))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load notification logs'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function sendDailySummary() {
    setSending(true)
    try {
      await notificationsApi.triggerDailySummary(selectedDate)
      toast.success(`Daily Summary dispatched for ${selectedDate}`)
      pushActivity({
        type: 'notification',
        title: 'Daily Summary Sent',
        detail: `Triggered daily summary for ${selectedDate}`,
      })
      await load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not trigger daily summary'))
    } finally {
      setSending(false)
    }
  }

  async function sendMonthlyPayroll() {
    setSending(true)
    try {
      const [year, month] = selectedDate.split('-').map(Number);
      await notificationsApi.triggerMonthlySummary(month, year)
      
      toast.success(`Monthly Payroll Summary dispatched for ${month}/${year}`)
      pushActivity({
        type: 'notification',
        title: 'Monthly Summary Sent',
        detail: `Triggered payroll summary for ${month}/${year}`,
      })
      await load()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not trigger payroll summary'))
    } finally {
      setSending(false)
    }
  }

  // Summary statistics
  const totalNotifications = logs.length
  const delivered = logs.filter((l) => l.status.toLowerCase() === 'sent').length
  const failed = logs.filter((l) => l.status.toLowerCase() === 'failed').length
  const successRate = totalNotifications ? Math.round((delivered / totalNotifications) * 100) : 0

  // Filtering and Searching
  const filteredLogs = logs.filter((log) => {
    if (statusFilter !== 'all' && log.status.toLowerCase() !== statusFilter) return false
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      return log.message.toLowerCase().includes(term) || log.status.toLowerCase().includes(term)
    }
    return true
  })

  // Helper to extract a friendly title from raw messages
  const getNotificationTitle = (message: string) => {
    if (message.includes('Payroll')) return 'Payroll Summary'
    if (message.includes('Daily')) return 'Daily Attendance Summary'
    if (message.includes('Alert')) return 'Smart Alert'
    return 'HR Notification'
  }

  // Helper to extract a date from message if possible (fallback to Recent)
  const extractDate = (message: string) => {
    const match = message.match(/\d{4}-\d{2}-\d{2}/)
    return match ? match[0] : 'Recent'
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notification History"
        subtitle="Review outgoing HR summaries and alerts."
        actions={
          <div className="flex items-center gap-2">
            <input 
              type="date" 
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 outline-none focus:border-brand-500 focus:ring-3 focus:ring-brand dark:border-ink-700 dark:bg-ink-900/60 dark:text-ink-100"
            />
            <Button disabled={sending} onClick={() => void sendDailySummary()}>
              <Send className="h-4 w-4" /> Daily
            </Button>
            <Button variant="secondary" disabled={sending} onClick={() => void sendMonthlyPayroll()}>
              <Send className="h-4 w-4" /> Monthly
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Sent" value={totalNotifications} accent="slate" />
        <StatCard label="Delivered" value={delivered} accent="green" />
        <StatCard label="Failed" value={failed} accent="rose" />
        <StatCard label="Success Rate" value={`${successRate}%`} accent="brand" />
      </div>

      <Card className="flex flex-col">
        <div className="flex flex-col gap-4 border-b border-ink-100 p-6 sm:flex-row sm:items-center sm:justify-between dark:border-ink-800">
          <h2 className="text-lg font-semibold text-ink-900 dark:text-ink-50">Delivery Logs</h2>
          <div className="flex items-center gap-3">
            <div className="w-48">
              <Input
                placeholder="Search messages..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="w-36">
              <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="all">All Statuses</option>
                <option value="sent">Delivered</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </Select>
            </div>
          </div>
        </div>

        <div className="p-0">
          {loading ? (
            <div className="p-6">
              <Skeleton className="h-80" />
            </div>
          ) : filteredLogs.length ? (
            <DataTable
              rows={filteredLogs}
              rowKey={(r) => r.id}
              pageSize={10}
              columns={[
                {
                  key: 'title',
                  header: 'Notification Title',
                  sortable: true,
                  sortValue: (r) => getNotificationTitle(r.message),
                  render: (r) => (
                    <span className="font-medium text-ink-900 dark:text-ink-100">
                      {getNotificationTitle(r.message)}
                    </span>
                  ),
                },
                {
                  key: 'date',
                  header: 'Date & Time',
                  render: (r) => <span className="text-ink-500 dark:text-ink-400">{extractDate(r.message)}</span>,
                },
                {
                  key: 'status',
                  header: 'Delivery Status',
                  sortable: true,
                  sortValue: (r) => r.status,
                  render: (r) => {
                    const isFailed = r.status.toLowerCase() === 'failed'
                    return (
                      <Badge tone={isFailed ? 'rose' : 'green'}>
                        {isFailed ? 'Delivery Failed' : 'Delivered'}
                      </Badge>
                    )
                  },
                },
                {
                  key: 'preview',
                  header: 'Preview',
                  render: (r) => (
                    <span className="line-clamp-1 max-w-[200px] text-ink-500 dark:text-ink-400">
                      {r.message}
                    </span>
                  ),
                },
                {
                  key: 'actions',
                  header: '',
                  className: 'text-right',
                  render: (r) => (
                    <Button variant="ghost" onClick={() => setSelectedLog(r)}>
                      View Details
                    </Button>
                  ),
                },
              ]}
            />
          ) : (
            <div className="p-6">
              <EmptyState title="No notifications found" description="Try adjusting your search or filters." />
            </div>
          )}
        </div>
      </Card>

      <Modal
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title={selectedLog ? getNotificationTitle(selectedLog.message) : ''}
      >
        {selectedLog && (
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-ink-500">Status:</span>
              <Badge tone={selectedLog.status.toLowerCase() === 'failed' ? 'rose' : 'green'}>
                {selectedLog.status.toLowerCase() === 'failed' ? 'Delivery Failed' : 'Delivered'}
              </Badge>
            </div>
            
            <div className="rounded-xl bg-ink-50 p-4 dark:bg-ink-950">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink-700 dark:text-ink-300">
                {selectedLog.message}
              </pre>
            </div>
            
            <div className="flex justify-end pt-2">
              <Button onClick={() => setSelectedLog(null)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}