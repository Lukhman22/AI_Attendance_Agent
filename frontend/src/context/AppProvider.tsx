import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AppContext } from './AppContext'
import type { ChatMessage } from './AppContext'
import type { ActivityItem } from '../types/api'
import { todayISO } from '../utils/format'

const THEME_KEY = 'hr_dashboard_theme'
const ACTIVITY_KEY = 'hr_dashboard_activity'
const AI_MESSAGES_KEY = 'hr_ai_messages'
const AI_WORK_DATE_KEY = 'hr_ai_work_date'

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

  // --- Persistent AI session state ---
  const [aiMessages, setAiMessagesState] = useState<ChatMessage[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(AI_MESSAGES_KEY) || '[]') as ChatMessage[]
    } catch {
      return []
    }
  })

  const [aiWorkDate, setAiWorkDateState] = useState<string>(() => {
    return localStorage.getItem(AI_WORK_DATE_KEY) || todayISO()
  })

  const [aiChatContext, setAiChatContextState] = useState<Record<string, unknown>>({})

  // Persist AI messages to localStorage (keep last 100)
  useEffect(() => {
    localStorage.setItem(AI_MESSAGES_KEY, JSON.stringify(aiMessages.slice(-100)))
  }, [aiMessages])

  // Persist AI work date
  useEffect(() => {
    localStorage.setItem(AI_WORK_DATE_KEY, aiWorkDate)
  }, [aiWorkDate])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    localStorage.setItem(THEME_KEY, darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(activity.slice(0, 40)))
  }, [activity])

  const setAiMessages = useCallback(
    (msgs: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => {
      setAiMessagesState(msgs)
    },
    [],
  )

  const setAiWorkDate = useCallback((date: string) => {
    setAiWorkDateState(date)
  }, [])

  const setAiChatContext = useCallback(
    (ctx: Record<string, unknown> | ((prev: Record<string, unknown>) => Record<string, unknown>)) => {
      setAiChatContextState(ctx)
    },
    [],
  )

  const clearAiConversation = useCallback(() => {
    setAiMessagesState([])
    setAiChatContextState({})
  }, [])

  const value = useMemo(
    () => ({
      darkMode,
      toggleDarkMode: () => setDarkMode((v) => !v),
      activity,
      pushActivity: (item: Omit<ActivityItem, 'id' | 'at'> & { at?: string }) => {
        setActivity((prev) =>
          [
            {
              id: crypto.randomUUID(),
              at: item.at ?? new Date().toISOString(),
              type: item.type,
              title: item.title,
              detail: item.detail,
            },
            ...prev,
          ].slice(0, 40),
        )
      },
      insightsRefreshKey,
      bumpInsightsRefresh: () => setInsightsRefreshKey((k) => k + 1),
      aiMessages,
      setAiMessages,
      aiWorkDate,
      setAiWorkDate,
      aiChatContext,
      setAiChatContext,
      clearAiConversation,
    }),
    [
      activity,
      darkMode,
      insightsRefreshKey,
      aiMessages,
      setAiMessages,
      aiWorkDate,
      setAiWorkDate,
      aiChatContext,
      setAiChatContext,
      clearAiConversation,
    ],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
