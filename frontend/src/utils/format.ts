export function formatMoney(value: number | string | null | undefined) {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatNumber(value: number | string | null | undefined, digits = 2) {
  const amount = Number(value ?? 0)
  return Number.isFinite(amount) ? amount.toFixed(digits) : '0.00'
}

export function formatPercent(value: number | string | null | undefined) {
  return `${formatNumber(value, 1)}%`
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

export function monthBounds(date = new Date()) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1)
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
  const toISO = (d: Date) => d.toISOString().slice(0, 10)
  return {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
    start: toISO(start),
    end: toISO(end),
  }
}

export function clsx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}
