import { NavLink, Outlet } from 'react-router-dom'
import {
  Bell,
  CalendarCheck2,
  FileBarChart2,
  LayoutDashboard,
  Menu,
  Moon,
  Settings,
  Sparkles,
  Sun,
  Users,
  Wallet,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Button } from './ui'
import { clsx } from '../utils/format'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/attendance', label: 'Attendance', icon: CalendarCheck2 },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/payroll', label: 'Payroll', icon: Wallet },
  { to: '/reports', label: 'Reports', icon: FileBarChart2 },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/ai-insights', label: 'AI Insights', icon: Sparkles },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function AppShell() {
  const { darkMode, toggleDarkMode } = useApp()
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(45,143,128,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(57,62,70,0.08),_transparent_28%)] dark:bg-[radial-gradient(circle_at_top_left,_rgba(45,143,128,0.16),_transparent_30%),linear-gradient(180deg,#0c2422_0%,#24282d_45%,#1a1f24_100%)]">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          className={clsx(
            'fixed inset-y-0 left-0 z-40 w-72 border-r border-ink-200/70 bg-white/95 p-5 backdrop-blur transition dark:border-ink-800 dark:bg-ink-950/95 lg:static lg:translate-x-0',
            open ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="font-display text-lg font-semibold text-brand-700 dark:text-brand-300">
                AI Attendance Agent
              </p>
              <p className="text-xs text-ink-500 dark:text-ink-400">HR Middleware Dashboard</p>
            </div>
            <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="space-y-1">
            {nav.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                      isActive
                        ? 'bg-brand-600 text-white shadow-soft'
                        : 'text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-900',
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>
        </aside>

        {open ? (
          <button
            className="fixed inset-0 z-30 bg-ink-950/40 lg:hidden"
            onClick={() => setOpen(false)}
            aria-label="Close overlay"
          />
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-ink-200/70 bg-white/75 px-4 py-3 backdrop-blur dark:border-ink-800 dark:bg-ink-950/70 sm:px-6">
            <div className="flex items-center gap-3">
              <button className="rounded-lg p-2 hover:bg-ink-100 dark:hover:bg-ink-900 lg:hidden" onClick={() => setOpen(true)}>
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <p className="text-sm font-medium text-ink-900 dark:text-ink-100">Employer Console</p>
                <p className="text-xs text-ink-500">Live data from FastAPI middleware</p>
              </div>
            </div>
            <Button variant="secondary" onClick={toggleDarkMode} aria-label="Toggle dark mode">
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {darkMode ? 'Light' : 'Dark'}
            </Button>
          </header>
          <main className="flex-1 p-4 sm:p-6 lg:p-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
