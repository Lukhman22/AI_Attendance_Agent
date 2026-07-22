import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { notificationsApi } from '../services'
import { getErrorMessage } from '../services/apiClient'
import type { NotificationSettings } from '../types/api'
import { Button, Card, Input, PageHeader, Skeleton } from '../components/ui'

export function SettingsPage() {
  const [settings, setSettings] = useState<NotificationSettings>({
    telegram_enabled: false,
    telegram_chat_id: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await notificationsApi.getSettings()
        setSettings({
          telegram_enabled: data.telegram_enabled || false,
          telegram_chat_id: data.telegram_chat_id || ''
        })
      } catch (error) {
        toast.error(getErrorMessage(error, 'Failed to load settings'))
      } finally {
        setLoading(false)
      }
    }
    void loadSettings()
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await notificationsApi.updateSettings(settings)
      toast.success('Notification settings saved successfully!')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to save settings'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Settings" subtitle="Configure application preferences." />
        <Skeleton className="h-64 mt-6 max-w-2xl" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader 
        title="Settings" 
        subtitle="Configure application preferences and notification providers." 
      />

      <div className="mt-6 max-w-2xl space-y-6">

        {/* Telegram Settings */}
        <Card className="p-6">
          <h2 className="mb-5 text-xs font-bold uppercase tracking-widest text-ink-500 dark:text-ink-400">Telegram Integration</h2>
          <div className="space-y-4">
            <label className="group flex cursor-pointer items-start gap-3 rounded-lg border border-transparent p-1 transition-colors hover:bg-ink-50 dark:hover:bg-ink-900/40">
              <input
                type="checkbox"
                name="telegram_enabled"
                checked={settings.telegram_enabled}
                onChange={handleChange}
                className="mt-0.5 h-4 w-4 rounded border-ink-300 text-brand-600 transition focus:ring-brand-500 dark:border-ink-700 dark:bg-ink-900"
              />
              <span className="text-[13px] font-medium text-ink-700 transition-colors group-hover:text-ink-900 dark:text-ink-200 dark:group-hover:text-ink-50">Enable Telegram Notifications</span>
            </label>

            {settings.telegram_enabled && (
              <div className="pl-7 mt-2">
                <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
                  Chat ID
                </label>
                <Input
                  type="text"
                  name="telegram_chat_id"
                  value={settings.telegram_chat_id || ''}
                  onChange={handleChange}
                  placeholder="-100123456789"
                />
                <p className="mt-1.5 text-xs text-ink-500 dark:text-ink-400">
                  The Chat ID of the group or user to receive alerts.
                </p>
              </div>
            )}
          </div>
        </Card>

        <div className="flex justify-end">
          <Button onClick={() => void handleSave()} disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>
    </div>
  )
}