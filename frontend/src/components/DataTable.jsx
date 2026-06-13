import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, Download, Search } from 'lucide-react'

export default function DataTable({
  columns = [],
  data = [],
  pageSize = 15,
  searchable = true,
  exportable = true,
  loading = false,
}) {
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!search.trim()) return data
    const query = search.toLowerCase()
    return data.filter((row) =>
      columns.some((col) => {
        const val = row[col.key]
        return val != null && String(val).toLowerCase().includes(query)
      })
    )
  }, [data, search, columns])

  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal
      }
      return sortDir === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })
  }, [filtered, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const paged = sorted.slice((page - 1) * pageSize, page * pageSize)

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function SortIcon({ column }) {
    if (sortKey !== column) return <ChevronsUpDown className="w-3.5 h-3.5 text-dark-text opacity-50" />
    return sortDir === 'asc' ? (
      <ChevronUp className="w-3.5 h-3.5 text-primary" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-primary" />
    )
  }

  function handleExport() {
    const headers = columns.map((c) => c.label || c.key).join(',')
    const rows = sorted.map((row) =>
      columns.map((col) => {
        const val = row[col.key]
        if (val == null) return ''
        const str = String(val)
        return str.includes(',') ? `"${str}"` : str
      }).join(',')
    )
    const csv = [headers, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `healthcare_data_export_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="bg-dark-card rounded-xl border border-dark-border overflow-hidden">
        <div className="p-4 border-b border-dark-border">
          <div className="h-8 bg-dark-border rounded w-48 animate-pulse" />
        </div>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex gap-4 p-3 border-b border-dark-border/50 animate-pulse">
            {columns.map((_, j) => (
              <div key={j} className="h-4 bg-dark-border rounded flex-1" />
            ))}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-dark-card rounded-xl border border-dark-border overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-dark-border">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          {searchable && (
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-text" />
              <input
                type="text"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1) }}
                placeholder="Search records..."
                className="w-full bg-dark-bg border border-dark-border rounded-lg pl-9 pr-3 py-2 text-sm text-dark-heading placeholder-dark-text focus:outline-none focus:border-primary/50 transition-colors"
              />
            </div>
          )}
        </div>
        {exportable && (
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-2 text-xs text-dark-text hover:text-dark-heading border border-dark-border rounded-lg hover:border-primary/30 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left cursor-pointer select-none group"
                  onClick={() => handleSort(col.key)}
                  style={{ width: col.width }}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium text-dark-text uppercase tracking-wider">
                      {col.label || col.key}
                    </span>
                    <SortIcon column={col.key} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-12 text-dark-text">
                  <p className="text-sm">No records found</p>
                </td>
              </tr>
            ) : (
              paged.map((row, i) => (
                <tr
                  key={row.id || i}
                  className="border-b border-dark-border/50 hover:bg-dark-border/20 transition-colors"
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-sm text-dark-text">
                      {col.render ? col.render(row[col.key], row) : formatValue(row[col.key], col.format)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-4 py-3 border-t border-dark-border">
        <p className="text-xs text-dark-text">
          Showing {sorted.length === 0 ? 0 : (page - 1) * pageSize + 1} to{' '}
          {Math.min(page * pageSize, sorted.length)} of {sorted.length} records
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs text-dark-text bg-dark-bg border border-dark-border rounded-lg disabled:opacity-50 hover:border-primary/30 transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-dark-text px-2">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs text-dark-text bg-dark-bg border border-dark-border rounded-lg disabled:opacity-50 hover:border-primary/30 transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

function formatValue(value, format) {
  if (value == null) return <span className="text-dark-text/50">—</span>
  if (format === 'number') return Number(value).toLocaleString()
  if (format === 'decimal') return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  if (format === 'date') {
    try { return new Date(value).toLocaleDateString() } catch { return value }
  }
  return String(value)
}
