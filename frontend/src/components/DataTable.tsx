import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, SearchX } from 'lucide-react'
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
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-ink-50/50 px-8 py-20 text-center dark:border-ink-800 dark:bg-ink-900/20">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400">
          <SearchX className="h-6 w-6" />
        </div>
        <p className="font-display text-base font-semibold text-ink-900 dark:text-ink-100">{emptyTitle}</p>
        <p className="mt-2 text-sm text-ink-500 dark:text-ink-400">{emptyDescription}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col overflow-hidden rounded-2xl border border-ink-200/60 bg-white shadow-sm dark:border-ink-800/60 dark:bg-ink-950">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-ink-100 dark:border-ink-800">
              {columns.map((col) => (
                <th 
                  key={col.key} 
                  className={clsx(
                    'sticky top-0 z-10 bg-ink-50/95 px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-ink-500 backdrop-blur-md dark:bg-ink-900/95 dark:text-ink-400', 
                    col.className
                  )}
                >
                  {col.sortable ? (
                    <button
                      className="group inline-flex items-center gap-1.5 hover:text-ink-900 transition-colors focus:outline-none dark:hover:text-ink-100"
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
                      <span className="flex items-center text-ink-400 transition-colors group-hover:text-ink-600 dark:text-ink-600 dark:group-hover:text-ink-400">
                        {sortKey === col.key ? (
                          sortDir === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100" />
                        )}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100 dark:divide-ink-800/60">
            {current.map((row) => (
              <tr
                key={rowKey(row)}
                className="group bg-white transition-colors hover:bg-ink-50/80 dark:bg-ink-950 dark:hover:bg-ink-900/50"
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx('px-6 py-4 align-middle text-[14px] text-ink-700 dark:text-ink-200', col.className)}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Pagination Footer */}
      <div className="flex items-center justify-between border-t border-ink-100 bg-white px-6 py-4 dark:border-ink-800 dark:bg-ink-950">
        <div className="text-[13px] text-ink-500 dark:text-ink-400">
          Showing <span className="font-semibold text-ink-900 dark:text-ink-100">{sorted.length === 0 ? 0 : page * pageSize + 1}</span> to <span className="font-semibold text-ink-900 dark:text-ink-100">{Math.min((page + 1) * pageSize, sorted.length)}</span> of <span className="font-semibold text-ink-900 dark:text-ink-100">{sorted.length}</span> results
        </div>
        <div className="flex items-center gap-1.5">
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-ink-200 text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-900 disabled:pointer-events-none disabled:opacity-40 dark:border-ink-700 dark:text-ink-400 dark:hover:bg-ink-800 dark:hover:text-ink-100"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            title="Previous Page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="flex h-8 items-center justify-center px-2 text-[13px] font-medium text-ink-700 dark:text-ink-300">
            Page {page + 1} of {pageCount}
          </div>
          <button
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-ink-200 text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-900 disabled:pointer-events-none disabled:opacity-40 dark:border-ink-700 dark:text-ink-400 dark:hover:bg-ink-800 dark:hover:text-ink-100"
            disabled={page >= pageCount - 1}
            onClick={() => setPage((p) => p + 1)}
            title="Next Page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
