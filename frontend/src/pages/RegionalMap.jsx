import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { Globe, AlertTriangle, Filter } from 'lucide-react'
import HeatmapChart from '../components/HeatmapChart'
import TrendChart from '../components/TrendChart'
import PieChartCard from '../components/PieChartCard'
import KPICard from '../components/KPICard'
import { shortName, isInvalidDisease, isCleanRecord } from '../utils/countryMapping'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

export default function RegionalMap() {
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDisease, setSelectedDisease] = useState('all')

  useEffect(() => {
    let mounted = true
    async function fetchData() {
      try {
        const { data } = await API.get('/api/cases', { params: { per_page: 1000 } })
        if (mounted) setCases(data.data || [])
      } catch (err) {
        if (mounted) setError(err.message)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchData()
    return () => { mounted = false }
  }, [])

  const diseases = useMemo(() => {
    const set = new Set(cases.filter((c) => isCleanRecord(c)).map((c) => c.disease_name))
    return ['all', ...Array.from(set)]
  }, [cases])

  const filtered = useMemo(() => {
    let r = cases.filter((c) => isCleanRecord(c))
    if (selectedDisease !== 'all') r = r.filter((c) => c.disease_name === selectedDisease)
    return r
  }, [cases, selectedDisease])

  const byRegion = useMemo(() => {
    const map = {}
    filtered.forEach((c) => {
      const region = c.region_name || 'Unknown'
      if (!map[region]) {
        map[region] = { name: region, cases: 0, deaths: 0, per100k: 0, count: 0, diseases: new Set() }
      }
      map[region].cases += Number(c.case_count) || 0
      map[region].deaths += Number(c.deaths) || 0
      map[region].per100k = Math.max(map[region].per100k, Number(c.cases_per_100k) || 0)
      map[region].count += 1
      if (c.disease_name) map[region].diseases.add(c.disease_name)
    })
    return Object.values(map).sort((a, b) => b.cases - a.cases).slice(0, 30).map((r) => ({ ...r, diseases: r.diseases.size }))
  }, [filtered])

  const byRegionPer100k = useMemo(() => {
    return [...byRegion].sort((a, b) => b.per100k - a.per100k).slice(0, 30)
  }, [byRegion])

  const trendByRegion = useMemo(() => {
    const map = {}
    filtered.forEach((c) => {
      const region = c.region_name || 'Unknown'
      const year = c.year
      if (!map[region]) map[region] = {}
      if (!map[region][year]) map[region][year] = 0
      map[region][year] += Number(c.case_count) || 0
    })
    const regions = Object.keys(map).slice(0, 5)
    const years = new Set()
    filtered.forEach((c) => { if (c.year) years.add(c.year) })
    const sortedYears = Array.from(years).sort()
    return sortedYears.map((year) => {
      const point = { year }
      regions.forEach((r) => { point[r] = map[r][year] || 0 })
      return point
    })
  }, [filtered])

  const regionLines = useMemo(() => {
    const regions = Object.keys(filtered.reduce((acc, c) => { if (c.region_name) acc[c.region_name] = true; return acc }, {})).slice(0, 5)
    const colors = ['#0D7C66', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6']
    return regions.map((r, i) => ({
      dataKey: r, name: shortName(r), color: colors[i % colors.length],
    }))
  }, [filtered])

  const diseaseDist = useMemo(() => {
    const map = {}
    filtered.forEach((c) => {
      const name = c.disease_name
      if (isInvalidDisease(name)) return
      if (!map[name]) map[name] = 0
      map[name] += Number(c.case_count) || 0
    })
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  }, [filtered])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-7 bg-dark-border rounded w-48 animate-pulse mb-2" />
        <div className="h-4 bg-dark-border rounded w-64 animate-pulse mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-dark-card rounded-xl border border-dark-border p-5 animate-pulse">
              <div className="h-4 bg-dark-border rounded w-24 mb-3" />
              <div className="h-8 bg-dark-border rounded w-32" />
            </div>
          ))}
        </div>
        <div className="h-96 bg-dark-card rounded-xl border border-dark-border animate-pulse" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-dark-heading text-lg font-medium mb-2">Region Data Unavailable</h2>
        <p className="text-dark-text text-sm">{error}</p>
      </div>
    )
  }

  const maxRegion = byRegion[0] || { cases: 0 }
  const maxPer100k = byRegionPer100k[0] || { per100k: 0 }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-heading">Regional Analysis</h1>
          <p className="text-dark-text text-sm mt-1">Disease burden across top 30 regions</p>
        </div>
        <div className="flex items-center gap-2 bg-dark-card border border-dark-border rounded-lg px-3 py-1.5">
          <Filter className="w-4 h-4 text-dark-text" />
          <select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="bg-transparent text-dark-heading text-sm focus:outline-none"
          >
            {diseases.map((d) => (
              <option key={d} value={d} className="bg-dark-card">{d === 'all' ? 'All Diseases' : d}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard title="Regions with Data" value={byRegion.length} subtitle="Top 30 displayed" icon={Globe} />
        <KPICard title="Highest Case Load" value={shortName(maxRegion.name)} subtitle={`${Number(maxRegion.cases).toLocaleString()} cases`} color="red" />
        <KPICard title="Highest per 100k" value={shortName(maxPer100k.name)} subtitle={`${Number(maxPer100k.per100k).toFixed(1)} per 100k`} color="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-dark-heading mb-3">Total Cases by Region</h2>
          <HeatmapChart
            data={byRegion.map((r) => ({ name: r.name, value: r.cases }))}
            xKey="name"
            valueKey="value"
            height={Math.max(400, byRegion.length * 22)}
            shortenLabels={true}
          />
        </div>
        <div>
          <PieChartCard data={diseaseDist} title="Disease Distribution" height={360} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold text-dark-heading mb-3">Cases per 100k by Region</h2>
          <HeatmapChart
            data={byRegionPer100k.map((r) => ({ name: r.name, value: r.per100k }))}
            xKey="name"
            valueKey="value"
            height={Math.max(400, byRegionPer100k.length * 22)}
            shortenLabels={true}
          />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-dark-heading mb-3">Regional Trends (Top 5)</h2>
          {regionLines.length > 0 ? (
            <TrendChart data={trendByRegion} lines={regionLines} height={380} />
          ) : (
            <div className="flex items-center justify-center h-64 bg-dark-card rounded-xl border border-dark-border">
              <p className="text-dark-text">No trend data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
