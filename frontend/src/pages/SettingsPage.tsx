import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { employeesApi, systemApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import { Button, Card, PageHeader } from '../components/ui'
import { useApp } from '../context/AppContext'

export function SettingsPage() {
  const { darkMode, toggleDarkMode } = useApp()
  const [health, setHealth] = useState<string>('checking…')
  const [seeding, setSeeding] = useState(false)

  useEffect(() => {
    systemApi
      .health()
      .then((h) => setHealth(`${h.status} · ${h.environment}`))
      .catch(() => setHealth('unreachable'))
  }, [])

  async function seedRules() {
    setSeeding(true)
    try {
      const result = await employeesApi.seedRules()
      toast.success(`Salary rules seeded (${result.name || 'default'})`)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to seed salary rules'))
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="System health, appearance, and default HR rule seeding."
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="space-y-4 p-5">
          <h2 className="font-display text-lg font-semibold">System</h2>
          <div className="rounded-xl bg-ink-50 p-3 text-sm dark:bg-ink-900/50">
            API health: <span className="font-medium">{health}</span>
          </div>
          <Button variant="secondary" onClick={toggleDarkMode}>
            Toggle {darkMode ? 'Light' : 'Dark'} Mode
          </Button>
          <Button onClick={() => void seedRules()} disabled={seeding}>
            {seeding ? 'Seeding…' : 'Seed default salary rules'}
          </Button>
          <p className="text-xs text-ink-500">
            HR rules (min hours, overtime, break validation) are configured via environment variables.
            Run <code className="rounded bg-ink-100 px-1 dark:bg-ink-800">python scripts/seed_demo.py</code>{' '}
            after migrations to load sample employees and attendance.
          </p>
        </Card>

        <Card className="space-y-4 p-5">
          <h2 className="font-display text-lg font-semibold">Notifications</h2>
          <p className="text-sm text-ink-600 dark:text-ink-300">
            Telegram and WhatsApp providers are configured through <code>NOTIFICATION_PROVIDER</code> and related
            environment variables. Daily attendance summaries are sent automatically after upload when{' '}
            <code>AI_AUTO_NOTIFY=true</code>. Monthly payroll summaries are sent when payroll is generated.
          </p>
        </Card>
      </div>
    </div>
  )
}
