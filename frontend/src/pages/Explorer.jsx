import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { Search, Filter, SlidersHorizontal, Download, AlertTriangle, Database, RotateCcw } from 'lucide-react'
import DataTable from '../components/DataTable'
import PieChartCard from '../components/PieChartCard'
import { shortName, isInvalidDisease, isCleanRecord } from '../utils/countryMapping'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

const TABLE_COLUMNS = [
  { key: 'disease_name', label: 'Disease', width: '16%' },
  { key: 'disease_category', label: 'Category', width: '12%' },
  { key: 'region_name', label: 'Region', width: '12%', render: (v) => shortName(v) },
  { key: 'continent', label: 'Continent', width: '10%' },
  { key: 'year', label: 'Year', width: '7%', format: 'number' },
  { key: 'age_group_name', label: 'Age Group', width: '10%' },
  { key: 'case_count', label: 'Cases', width: '10%', format: 'number' },
  { key: 'cases_per_100k', label: 'Per 100k', width: '8%', format: 'decimal' },
  { key: 'source', label: 'Source', width: '8%' },
]

export default function Explorer() {
  const [data, setData] = useState([])
  const [diseases, setDiseases] = useState([])
  const [regions, setRegions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ disease: '', region: '', year: '', source: '', sort_by: 'loaded_at', sort_order: 'desc' })
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ total: 0, total_pages: 1 })

  const diseaseNames = useMemo(() => new Set(diseases.map((d) => d.disease_name)), [diseases])

  useEffect(() => {
    async function fetchMeta() {
      try {
        const [dRes, rRes] = await Promise.all([API.get('/api/diseases'), API.get('/api/regions')])
        const loaded = dRes.data.data || []
        setDiseases(loaded)
        setRegions(rRes.data.data || [])
        const validNames = new Set(loaded.map((d) => d.disease_name))
        setFilters((prev) => {
          if (prev.disease && !validNames.has(prev.disease)) return { ...prev, disease: '' }
          return prev
        })
      } catch (err) { console.warn('Could not load filter options:', err.message) }
    }
    fetchMeta()
  }, [])

  useEffect(() => {
    let mounted = true
    async function fetchData() {
      setLoading(true)
      try {
        const params = { page, per_page: 50, sort_by: filters.sort_by, sort_order: filters.sort_order }
        if (filters.disease) params.disease = filters.disease
        if (filters.region) params.region = filters.region
        if (filters.year) params.year = parseInt(filters.year)
        if (filters.source) params.source = filters.source
        const { data: res } = await API.get('/api/cases', { params })
        if (mounted) { setData(res.data || []); setPagination(res.pagination || { total: 0, total_pages: 1 }) }
      } catch (err) { if (mounted) setError(err.message) }
      finally { if (mounted) setLoading(false) }
    }
    fetchData()
    return () => { mounted = false }
  }, [page, filters])

  function handleFilterChange(key, value) { setFilters((prev) => ({ ...prev, [key]: value })); setPage(1) }
  function resetFilters() { setFilters({ disease: '', region: '', year: '', source: '', sort_by: 'loaded_at', sort_order: 'desc' }); setPage(1) }

  const filterCount = useMemo(() => {
    return Object.entries(filters).filter(([key, val]) => key !== 'sort_by' && key !== 'sort_order' && val).length
  }, [filters])

  const diseaseDist = useMemo(() => {
    const map = {}
    data.forEach((c) => {
      const name = c.disease_name
      if (isInvalidDisease(name)) return
      if (!map[name]) map[name] = 0
      map[name] += Number(c.case_count) || 0
    })
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  }, [data])

  if (error && data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-dark-heading text-lg font-medium mb-2">Query Failed</h2>
        <p className="text-dark-text text-sm">{error}</p>
        <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/80 transition-colors">Retry</button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-heading">Data Explorer</h1>
          <p className="text-dark-text text-sm mt-1">Multi-dimensional query interface &middot; {pagination.total} records available</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={resetFilters} className="flex items-center gap-2 px-3 py-2 text-xs text-dark-text border border-dark-border rounded-lg hover:border-primary/30 transition-all">
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </button>
          <div className="flex items-center gap-2 bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-xs text-dark-text">
            <Database className="w-3.5 h-3.5" /> {pagination.total} records
          </div>
        </div>
      </div>

      <div className="bg-dark-card rounded-xl border border-dark-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-dark-heading">Filters</span>
          {filterCount > 0 && <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">{filterCount} active</span>}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-dark-text mb-1">Disease</label>
            <select value={filters.disease} onChange={(e) => handleFilterChange('disease', e.target.value)} className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-heading focus:outline-none focus:border-primary/50">
              <option value="">All Diseases</option>
              {diseases.filter((d) => !isInvalidDisease(d.disease_name)).map((d) => (
                <option key={d.disease_id} value={d.disease_name}>{d.disease_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-dark-text mb-1">Region</label>
            <select value={filters.region} onChange={(e) => handleFilterChange('region', e.target.value)} className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-heading focus:outline-none focus:border-primary/50">
              <option value="">All Regions</option>
              {regions.map((r) => (
                <option key={r.region_id} value={r.region_name}>{shortName(r.region_name)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-dark-text mb-1">Year</label>
            <input type="number" value={filters.year} onChange={(e) => handleFilterChange('year', e.target.value)} placeholder="e.g. 2024" className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-heading placeholder-dark-text focus:outline-none focus:border-primary/50" />
          </div>
          <div>
            <label className="block text-xs text-dark-text mb-1">Source</label>
            <select value={filters.source} onChange={(e) => handleFilterChange('source', e.target.value)} className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-heading focus:outline-none focus:border-primary/50">
              <option value="">All Sources</option>
              <option value="WHO">WHO</option><option value="OWID">OWID</option><option value="CDC">CDC</option>
            </select>
          </div>
        </div>
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-dark-border">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5 text-dark-text" />
            <span className="text-xs text-dark-text">Sort by:</span>
            <select value={filters.sort_by} onChange={(e) => handleFilterChange('sort_by', e.target.value)} className="bg-dark-bg border border-dark-border rounded px-2 py-1 text-xs text-dark-heading focus:outline-none">
              <option value="loaded_at">Date Added</option>
              <option value="year">Year</option>
              <option value="case_count">Case Count</option>
              <option value="disease">Disease Name</option>
            </select>
            <button onClick={() => handleFilterChange('sort_order', filters.sort_order === 'desc' ? 'asc' : 'desc')} className="px-2 py-1 text-xs bg-dark-bg border border-dark-border rounded hover:border-primary/30 transition-colors text-dark-text">
              {filters.sort_order === 'desc' ? 'DESC' : 'ASC'}
            </button>
          </div>
          <button onClick={() => { const csv = [TABLE_COLUMNS.map((c) => c.label).join(',')]; data.forEach((row) => { csv.push(TABLE_COLUMNS.map((c) => String(row[c.key] || '')).join(',')) }); const blob = new Blob([csv.join('\n')], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `explorer_export_${new Date().toISOString().split('T')[0]}.csv`; a.click(); URL.revokeObjectURL(url) }} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-dark-text border border-dark-border rounded-lg hover:border-primary/30 hover:text-dark-heading transition-all">
            <Download className="w-3.5 h-3.5" /> Export Page
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <DataTable columns={TABLE_COLUMNS} data={data} loading={loading} pageSize={50} exportable={false} />
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-4 py-2 text-sm text-dark-text bg-dark-card border border-dark-border rounded-lg disabled:opacity-50 hover:border-primary/30 transition-colors">Previous</button>
              {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => { const start = Math.max(1, page - 2); const p = start + i; if (p > pagination.total_pages) return null; return (<button key={p} onClick={() => setPage(p)} className={`w-9 h-9 text-sm rounded-lg transition-colors ${p === page ? 'bg-primary text-white' : 'bg-dark-card text-dark-text border border-dark-border hover:border-primary/30'}`}>{p}</button>) })}
              <button onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))} disabled={page === pagination.total_pages} className="px-4 py-2 text-sm text-dark-text bg-dark-card border border-dark-border rounded-lg disabled:opacity-50 hover:border-primary/30 transition-colors">Next</button>
            </div>
          )}
        </div>
        <div>
          <PieChartCard data={diseaseDist} title="Disease Distribution (Page)" height={360} />
        </div>
      </div>
    </div>
  )
}
