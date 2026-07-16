import { createContext, useContext } from 'react'
import type { ActivityItem } from '../types/api'

export interface AppContextValue {
  darkMode: boolean
  toggleDarkMode: () => void
  activity: ActivityItem[]
  pushActivity: (item: Omit<ActivityItem, 'id' | 'at'> & { at?: string }) => void
  insightsRefreshKey: number
  bumpInsightsRefresh: () => void
}

export const AppContext = createContext<AppContextValue | null>(null)

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
