import { createContext, useContext } from 'react'
import type { ActivityItem } from '../types/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  references?: Record<string, unknown>
  isError?: boolean
  timestamp?: number
}

export interface AppContextValue {
  darkMode: boolean
  toggleDarkMode: () => void
  activity: ActivityItem[]
  pushActivity: (item: Omit<ActivityItem, 'id' | 'at'> & { at?: string }) => void
  insightsRefreshKey: number
  bumpInsightsRefresh: () => void
  // Persistent AI Insights session
  aiMessages: ChatMessage[]
  setAiMessages: (msgs: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void
  aiWorkDate: string
  setAiWorkDate: (date: string) => void
  aiChatContext: Record<string, unknown>
  setAiChatContext: (ctx: Record<string, unknown> | ((prev: Record<string, unknown>) => Record<string, unknown>)) => void
  clearAiConversation: () => void
}

export const AppContext = createContext<AppContextValue | null>(null)

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
