import { clsx } from '../utils/format'
import type { ReactNode } from 'react'

export function Card({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-ink-200/80 bg-white/90 shadow-soft backdrop-blur dark:border-ink-800 dark:bg-ink-900/80',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-950 dark:text-white sm:text-3xl">
          {title}
        </h1>
        {subtitle ? <p className="mt-1 text-sm text-ink-500 dark:text-ink-300">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function StatCard({
  label,
  value,
  hint,
  accent = 'brand',
}: {
  label: string
  value: string | number
  hint?: string
  accent?: 'brand' | 'amber' | 'rose' | 'sky' | 'slate'
}) {
  const accents = {
    brand: 'from-brand-500/15 to-transparent text-brand-700 dark:text-brand-300',
    amber: 'from-amber-500/15 to-transparent text-amber-700 dark:text-amber-300',
    rose: 'from-rose-500/15 to-transparent text-rose-700 dark:text-rose-300',
    sky: 'from-sky-500/15 to-transparent text-sky-700 dark:text-sky-300',
    slate: 'from-slate-500/15 to-transparent text-slate-700 dark:text-slate-300',
  }
  return (
    <Card className={clsx('overflow-hidden bg-gradient-to-br p-5', accents[accent])}>
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-ink-500 dark:text-ink-300">
        {label}
      </p>
      <p className="mt-3 font-display text-3xl font-semibold text-ink-950 dark:text-white">{value}</p>
      {hint ? <p className="mt-2 text-xs text-ink-500 dark:text-ink-400">{hint}</p> : null}
    </Card>
  )
}

export function Button({
  children,
  variant = 'primary',
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  const styles = {
    primary:
      'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-600/50',
    secondary:
      'border border-ink-200 bg-white text-ink-800 hover:bg-ink-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-100 dark:hover:bg-ink-800',
    ghost: 'text-ink-600 hover:bg-ink-100 dark:text-ink-200 dark:hover:bg-ink-800',
    danger: 'bg-rose-600 text-white hover:bg-rose-700',
  }
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed',
        styles[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        'w-full rounded-xl border border-ink-200 bg-white px-3 py-2.5 text-sm text-ink-900 outline-none ring-brand-500/30 placeholder:text-ink-400 focus:ring-2 dark:border-ink-700 dark:bg-ink-950 dark:text-ink-100',
        props.className,
      )}
    />
  )
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={clsx(
        'w-full rounded-xl border border-ink-200 bg-white px-3 py-2.5 text-sm text-ink-900 outline-none ring-brand-500/30 focus:ring-2 dark:border-ink-700 dark:bg-ink-950 dark:text-ink-100',
        props.className,
      )}
    />
  )
}

export function Badge({
  children,
  tone = 'slate',
}: {
  children: ReactNode
  tone?: 'green' | 'rose' | 'amber' | 'slate' | 'sky'
}) {
  const tones = {
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
    rose: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
    slate: 'bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-200',
    sky: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
  }
  return (
    <span className={clsx('inline-flex rounded-full px-2.5 py-1 text-xs font-medium capitalize', tones[tone])}>
      {children}
    </span>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-300 px-6 py-16 text-center dark:border-ink-700">
      <p className="font-display text-lg font-semibold text-ink-800 dark:text-ink-100">{title}</p>
      <p className="mt-2 max-w-md text-sm text-ink-500 dark:text-ink-400">{description}</p>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded-xl bg-ink-200/80 dark:bg-ink-800/80',
        className,
      )}
    />
  )
}

export function PendingBackend({ feature }: { feature: string }) {
  return (
    <div className="rounded-xl border border-amber-300/70 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100">
      Pending Backend Support: {feature}
    </div>
  )
}

export function statusTone(status: string): 'green' | 'rose' | 'amber' | 'slate' | 'sky' {
  const value = status.toLowerCase()
  if (value === 'present' || value === 'sent' || value === 'generated') return 'green'
  if (value === 'absent' || value === 'failed') return 'rose'
  if (value.includes('missing') || value === 'leave') return 'amber'
  if (value.includes('holiday') || value.includes('weekly')) return 'sky'
  return 'slate'
}
