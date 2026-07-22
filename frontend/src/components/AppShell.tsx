import { NavLink, Outlet, useLocation } from 'react-router-dom'
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

const mainNav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/attendance', label: 'Attendance', icon: CalendarCheck2 },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/payroll', label: 'Payroll', icon: Wallet },
]

const secondaryNav = [
  { to: '/reports', label: 'Reports', icon: FileBarChart2 },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/ai-insights', label: 'AI Insights', icon: Sparkles },
]

const bottomNav = [
  { to: '/settings', label: 'Settings', icon: Settings },
]

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/attendance': 'Attendance',
  '/employees': 'Employees',
  '/payroll': 'Payroll',
  '/reports': 'Reports',
  '/notifications': 'Notifications',
  '/ai-insights': 'AI Insights',
  '/settings': 'Settings',
}

function NavSection({ label, items, onNavigate }: { label?: string; items: typeof mainNav; onNavigate: () => void }) {
  return (
    <div>
      {label ? (
        <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-ink-400 dark:text-ink-500">
          {label}
        </p>
      ) : null}
      <div className="space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                clsx(
                  'group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors',
                  isActive
                    ? 'bg-brand-600 text-white shadow-soft'
                    : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900 dark:text-ink-400 dark:hover:bg-ink-800/70 dark:hover:text-ink-100',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          )
        })}
      </div>
    </div>
  )
}

export function AppShell() {
  const { darkMode, toggleDarkMode } = useApp()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const currentTitle = pageTitles[location.pathname] || ''

  const closeMobile = () => setOpen(false)

  return (
    <div className="min-h-screen bg-ink-50 dark:bg-ink-950">
      <div className="flex min-h-screen">
        {/* ── Sidebar ── */}
        <aside
          className={clsx(
            'fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-ink-200/50 bg-white transition-transform duration-200 dark:border-ink-800/50 dark:bg-ink-900/95 lg:static lg:translate-x-0',
            open ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          {/* Sidebar Header */}
          <div className="flex h-[57px] shrink-0 items-center justify-between border-b border-ink-100/80 px-5 dark:border-ink-800/40">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-[11px] font-bold text-white">
                AI
              </div>
              <div className="leading-none">
                <p className="font-display text-sm font-semibold text-ink-900 dark:text-ink-50">
                  Attendance
                </p>
                <p className="text-[11px] text-ink-400 dark:text-ink-500">HR Middleware</p>
              </div>
            </div>
            <button className="rounded-lg p-1 hover:bg-ink-100 dark:hover:bg-ink-800 lg:hidden" onClick={closeMobile} aria-label="Close menu">
              <X className="h-4 w-4 text-ink-500" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-4">
            <NavSection items={mainNav} onNavigate={closeMobile} />
            <NavSection label="Tools" items={secondaryNav} onNavigate={closeMobile} />
            <div className="mt-auto">
              <NavSection items={bottomNav} onNavigate={closeMobile} />
            </div>
          </nav>
        </aside>

        {/* Mobile overlay */}
        {open ? (
          <button
            className="fixed inset-0 z-30 bg-ink-950/30 backdrop-blur-sm lg:hidden"
            onClick={closeMobile}
            aria-label="Close overlay"
          />
        ) : null}

        {/* ── Main Area ── */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Top Header */}
          <header className="sticky top-0 z-20 flex h-[57px] shrink-0 items-center justify-between border-b border-ink-200/50 bg-white/85 px-6 backdrop-blur-xl dark:border-ink-800/50 dark:bg-ink-950/85">
            <div className="flex items-center gap-3">
              <button className="rounded-lg p-1.5 hover:bg-ink-100 dark:hover:bg-ink-800 lg:hidden" onClick={() => setOpen(true)}>
                <Menu className="h-5 w-5 text-ink-600 dark:text-ink-300" />
              </button>
              <p className="font-display text-sm font-semibold text-ink-900 dark:text-ink-50">
                {currentTitle}
              </p>
            </div>
            <Button variant="ghost" onClick={toggleDarkMode} aria-label="Toggle dark mode" className="gap-1.5 text-ink-500">
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              <span className="hidden text-xs sm:inline">{darkMode ? 'Light' : 'Dark'}</span>
            </Button>
          </header>

          {/* Page Content */}
          <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
            <div key={location.pathname} className="mx-auto max-w-[1280px] animate-fade-in">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
