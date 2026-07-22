import { clsx } from '../utils/format'
import React, { type ReactNode, forwardRef } from 'react'

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
        'animate-slide-up rounded-xl border border-ink-200/60 bg-white shadow-card transition-all duration-300 dark:border-ink-800/60 dark:bg-ink-900/70',
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
    <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between animate-slide-down">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900 dark:text-ink-50 sm:text-3xl">
          {title}
        </h1>
        {subtitle ? <p className="mt-2 text-sm leading-relaxed text-ink-500 dark:text-ink-400">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2.5">{actions}</div> : null}
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
  accent?: 'brand' | 'amber' | 'rose' | 'sky' | 'slate' | 'green'
}) {
  const accents = {
    brand: 'from-brand-500/10 to-transparent text-brand-700 dark:from-brand-500/12 dark:text-brand-300',
    amber: 'from-amber-500/10 to-transparent text-amber-700 dark:from-amber-500/12 dark:text-amber-300',
    rose: 'from-rose-500/10 to-transparent text-rose-700 dark:from-rose-500/12 dark:text-rose-300',
    sky: 'from-sky-500/10 to-transparent text-sky-700 dark:from-sky-500/12 dark:text-sky-300',
    slate: 'from-ink-400/8 to-transparent text-ink-600 dark:from-ink-400/10 dark:text-ink-300',
    green: 'from-emerald-500/10 to-transparent text-emerald-700 dark:from-emerald-500/12 dark:text-emerald-300',
  }
  return (
    <Card className={clsx('overflow-hidden bg-gradient-to-br p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-elevated', accents[accent])}>
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-ink-500 dark:text-ink-400">
        {label}
      </p>
      <p className="mt-3 font-display text-3xl font-semibold text-ink-900 dark:text-ink-50">{value}</p>
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
      'bg-brand-600 text-white shadow-soft hover:bg-brand-700 active:bg-brand-800 disabled:opacity-50 disabled:hover:bg-brand-600',
    secondary:
      'border border-ink-200 bg-white text-ink-700 shadow-soft hover:bg-ink-50 active:bg-ink-100 dark:border-ink-700 dark:bg-ink-800/60 dark:text-ink-200 dark:hover:bg-ink-800 dark:active:bg-ink-700',
    ghost:
      'text-ink-600 hover:bg-ink-100 active:bg-ink-150 dark:text-ink-300 dark:hover:bg-ink-800 dark:active:bg-ink-700',
    danger:
      'bg-rose-600 text-white shadow-soft hover:bg-rose-700 active:bg-rose-800',
  }
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-brand disabled:pointer-events-none disabled:opacity-50',
        styles[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  (props, ref) => {
    return (
      <input
        {...props}
        ref={ref}
        className={clsx(
          'w-full rounded-xl border-0 px-4 py-2.5 text-[14px] text-ink-900 shadow-sm ring-1 ring-inset ring-ink-200 transition-all placeholder:text-ink-400 focus:ring-2 focus:ring-inset focus:ring-brand-500 outline-none dark:bg-ink-900/50 dark:text-ink-100 dark:ring-ink-800 dark:placeholder:text-ink-600 dark:focus:ring-brand-500 sm:leading-6',
          props.className,
        )}
      />
    )
  }
)
Input.displayName = 'Input'

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  (props, ref) => {
    return (
      <select
        {...props}
        ref={ref}
        className={clsx(
          'w-full rounded-xl border-0 px-4 py-2.5 text-[14px] text-ink-900 shadow-sm ring-1 ring-inset ring-ink-200 transition-all focus:ring-2 focus:ring-inset focus:ring-brand-500 outline-none dark:bg-ink-900/50 dark:text-ink-100 dark:ring-ink-800 dark:focus:ring-brand-500 sm:leading-6',
          props.className,
        )}
      />
    )
  }
)
Select.displayName = 'Select'

export function Badge({
  children,
  tone = 'slate',
}: {
  children: ReactNode
  tone?: 'green' | 'rose' | 'amber' | 'slate' | 'sky'
}) {
  const tones = {
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20',
    rose: 'bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-400 dark:ring-rose-500/20',
    amber: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20',
    slate: 'bg-ink-50 text-ink-600 ring-ink-500/20 dark:bg-ink-400/10 dark:text-ink-400 dark:ring-ink-400/20',
    sky: 'bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-400 dark:ring-sky-500/20',
  }
  return (
    <span className={clsx('inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset', tones[tone])}>
      {children}
    </span>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-ink-50/50 px-6 py-16 text-center dark:border-ink-800 dark:bg-ink-900/20">
      <p className="font-display text-base font-semibold text-ink-900 dark:text-ink-100">{title}</p>
      <p className="mt-2 max-w-md text-sm text-ink-500 dark:text-ink-400">{description}</p>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'animate-pulse-slow rounded-xl bg-ink-100 dark:bg-ink-800/80',
        className,
      )}
    />
  )
}

export function PendingBackend({ feature }: { feature: string }) {
  return (
    <div className="rounded-lg border border-amber-200/70 bg-amber-50/80 px-3 py-2 text-xs text-amber-800 dark:border-amber-700/40 dark:bg-amber-950/30 dark:text-amber-200">
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

export function Modal({
  isOpen,
  onClose,
  title,
  children,
}: {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 backdrop-blur-sm p-4 animate-fade-in sm:p-0">
      <div 
        className="fixed inset-0" 
        onClick={onClose} 
        aria-hidden="true" 
      />
      <div className="relative animate-slide-up w-full max-w-lg rounded-2xl border border-ink-200/60 bg-white shadow-elevated dark:border-ink-800/60 dark:bg-ink-900">
        <div className="flex items-center justify-between border-b border-ink-100 px-6 py-4 dark:border-ink-800">
          <h3 className="font-display text-lg font-semibold text-ink-900 dark:text-ink-50">{title}</h3>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-600 dark:hover:bg-ink-800 dark:hover:text-ink-300"
          >
            <span className="text-xl leading-none">&times;</span>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
