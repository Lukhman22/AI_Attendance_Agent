import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { clsx } from '../utils/format'

export function DataTable<T>({
  rows,
  columns,
  pageSize = 10,
  emptyTitle = 'No records',
  emptyDescription = 'There is nothing to show yet.',
  rowKey,
}: {
  rows: T[]
  columns: Array<{
    key: string
    header: string
    sortable?: boolean
    className?: string
    render: (row: T) => ReactNode
    sortValue?: (row: T) => string | number
  }>
  pageSize?: number
  emptyTitle?: string
  emptyDescription?: string
  rowKey: (row: T) => string | number
}) {
  const [page, setPage] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const sorted = useMemo(() => {
    if (!sortKey) return rows
    const column = columns.find((c) => c.key === sortKey)
    if (!column?.sortValue) return rows
    return [...rows].sort((a, b) => {
      const av = column.sortValue!(a)
      const bv = column.sortValue!(b)
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [columns, rows, sortDir, sortKey])

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize))
  const current = sorted.slice(page * pageSize, page * pageSize + pageSize)

  if (!rows.length) {
    return (
      <div className="rounded-2xl border border-dashed border-ink-300 px-6 py-14 text-center dark:border-ink-700">
        <p className="font-display text-lg font-semibold">{emptyTitle}</p>
        <p className="mt-2 text-sm text-ink-500">{emptyDescription}</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-ink-200 dark:border-ink-800">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink-100/80 text-xs uppercase tracking-wide text-ink-500 dark:bg-ink-900 dark:text-ink-300">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={clsx('px-4 py-3 font-medium', col.className)}>
                  {col.sortable ? (
                    <button
                      className="inline-flex items-center gap-1"
                      onClick={() => {
                        if (sortKey === col.key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                        else {
                          setSortKey(col.key)
                          setSortDir('asc')
                        }
                        setPage(0)
                      }}
                    >
                      {col.header}
                      {sortKey === col.key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {current.map((row) => (
              <tr
                key={rowKey(row)}
                className="border-t border-ink-100 bg-white/70 dark:border-ink-800 dark:bg-ink-950/40"
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx('px-4 py-3 align-middle', col.className)}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-ink-100 bg-white/80 px-4 py-3 text-xs dark:border-ink-800 dark:bg-ink-950/60">
        <span>
          Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, sorted.length)} of {sorted.length}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-lg border px-2 py-1 disabled:opacity-40 dark:border-ink-700"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Prev
          </button>
          <button
            className="rounded-lg border px-2 py-1 disabled:opacity-40 dark:border-ink-700"
            disabled={page >= pageCount - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
