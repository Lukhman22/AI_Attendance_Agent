import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { settingsApi } from '../services/settingsApi'
import { getErrorMessage } from '../services/apiClient'
import type { NotificationSettings } from '../types/api'
import { Button, Card, Input, PageHeader, Skeleton } from '../components/ui'
import { Eye, EyeOff } from 'lucide-react'

export function SettingsPage() {
  const [settings, setSettings] = useState<NotificationSettings & { telegram_bot_token?: string }>({
    telegram_enabled: false,
    telegram_chat_id: '',
    telegram_bot_token: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [showToken, setShowToken] = useState(false)

  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await settingsApi.getSettings()
        setSettings({
          telegram_enabled: data.telegram_enabled || false,
          telegram_chat_id: data.telegram_chat_id || '',
          telegram_bot_token: data.telegram_bot_token || '',
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
      await settingsApi.updateSettings(settings)
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
              <div className="pl-7 mt-2 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-ink-500 dark:text-ink-400 mb-1">
                    Telegram Bot Token
                  </label>
                  <div className="relative">
                    <Input
                      type={showToken ? "text" : "password"}
                      name="telegram_bot_token"
                      value={settings.telegram_bot_token || ''}
                      onChange={handleChange}
                      placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-700"
                      onClick={() => setShowToken(!showToken)}
                    >
                      {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div>
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

                <div className="pt-2">
                  <Button 
                    variant="secondary" 
                    onClick={async () => {
                      if (!settings.telegram_bot_token || !settings.telegram_chat_id) {
                        toast.error('Token and Chat ID are required for testing');
                        return;
                      }
                      setTesting(true);
                      try {
                        await settingsApi.testTelegram(settings.telegram_bot_token, settings.telegram_chat_id);
                        toast.success('Test message sent successfully!');
                      } catch (error) {
                        toast.error(getErrorMessage(error, 'Test failed'));
                      } finally {
                        setTesting(false);
                      }
                    }} 
                    disabled={testing}
                  >
                    {testing ? 'Testing...' : 'Test Connection'}
                  </Button>
                </div>
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