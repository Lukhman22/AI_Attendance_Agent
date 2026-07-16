import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { AppContext } from './AppContext'
import type { ActivityItem } from '../types/api'

const THEME_KEY = 'hr_dashboard_theme'
const ACTIVITY_KEY = 'hr_dashboard_activity'

export function AppProvider({ children }: { children: ReactNode }) {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const [activity, setActivity] = useState<ActivityItem[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(ACTIVITY_KEY) || '[]') as ActivityItem[]
    } catch {
      return []
    }
  })
  const [insightsRefreshKey, setInsightsRefreshKey] = useState(0)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    localStorage.setItem(THEME_KEY, darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(activity.slice(0, 40)))
  }, [activity])

  const value = useMemo(
    () => ({
      darkMode,
      toggleDarkMode: () => setDarkMode((v) => !v),
      activity,
      pushActivity: (item: Omit<ActivityItem, 'id' | 'at'> & { at?: string }) => {
        setActivity((prev) => [
          {
            id: crypto.randomUUID(),
            at: item.at ?? new Date().toISOString(),
            type: item.type,
            title: item.title,
            detail: item.detail,
          },
          ...prev,
        ].slice(0, 40))
      },
      insightsRefreshKey,
      bumpInsightsRefresh: () => setInsightsRefreshKey((k) => k + 1),
    }),
    [activity, darkMode, insightsRefreshKey],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
