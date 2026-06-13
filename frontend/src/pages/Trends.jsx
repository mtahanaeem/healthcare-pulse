import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { TrendingUp, Filter, Calendar, AlertTriangle, TrendingDown } from 'lucide-react'
import TrendChart from '../components/TrendChart'
import PieChartCard from '../components/PieChartCard'
import KPICard from '../components/KPICard'
import { shortName, isInvalidDisease, isCleanRecord } from '../utils/countryMapping'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

export default function Trends() {
  const [cases, setCases] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDisease, setSelectedDisease] = useState('all')
  const [selectedRegion, setSelectedRegion] = useState('all')
  const [viewMode, setViewMode] = useState('overlay')

  useEffect(() => {
    let mounted = true
    async function fetchCases() {
      try {
        const { data } = await API.get('/api/cases', { params: { per_page: 500 } })
        if (mounted) setCases(data.data || [])
      } catch (err) {
        if (mounted) setError(err.message)
      }
    }
    async function fetchForecast() {
      try {
        const { data } = await API.get('/api/forecast', { params: { limit: 200 } })
        if (mounted) setForecast(data.data || [])
      } catch (err) {
        console.warn('Forecast unavailable:', err.message)
      }
    }
    Promise.all([fetchCases(), fetchForecast()]).finally(() => {
      if (mounted) setLoading(false)
    })
    const interval = setInterval(fetchCases, 60000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  const diseases = useMemo(() => {
    const set = new Set(cases.filter((c) => isCleanRecord(c)).map((c) => c.disease_name))
    return ['all', ...Array.from(set)]
  }, [cases])

  const regions = useMemo(() => {
    const set = new Set(cases.map((c) => c.region_name).filter(Boolean))
    return ['all', ...Array.from(set)]
  }, [cases])

  const filtered = useMemo(() => {
    let result = cases.filter((c) => isCleanRecord(c))
    if (selectedDisease !== 'all') result = result.filter((c) => c.disease_name === selectedDisease)
    if (selectedRegion !== 'all') result = result.filter((c) => c.region_name === selectedRegion)
    return result
  }, [cases, selectedDisease, selectedRegion])

  const trendData = useMemo(() => {
    const byYear = {}
    filtered.forEach((c) => {
      const year = c.year
      if (!byYear[year]) byYear[year] = { year, cases: 0, deaths: 0, recoveries: 0 }
      byYear[year].cases += Number(c.case_count) || 0
      byYear[year].deaths += Number(c.deaths) || 0
      byYear[year].recoveries += Number(c.recoveries) || 0
    })
    return Object.values(byYear).sort((a, b) => a.year - b.year)
  }, [filtered])

  const forecastTrendData = useMemo(() => {
    const byYear = {}
    forecast.forEach((f) => {
      const year = f.year
      if (!byYear[year]) byYear[year] = { year, actual: 0, predicted: 0 }
      byYear[year].predicted += Number(f.prediction) || 0
      if (f.case_count) byYear[year].actual += Number(f.case_count) || 0
    })
    return Object.values(byYear).sort((a, b) => a.year - b.year)
  }, [forecast])

  const combinedData = useMemo(() => {
    if (viewMode === 'forecast') return forecastTrendData
    if (viewMode !== 'overlay') return trendData
    if (forecastTrendData.length === 0) return trendData
    const lastYear = trendData.length > 0 ? trendData[trendData.length - 1].year : 0
    const historical = trendData.filter((d) => d.year <= lastYear)
    const fc = forecastTrendData.filter((f) => {
      const match = trendData.find((h) => h.year === f.year)
      return !match || f.predicted !== f.actual
    })
    const merged = [...historical]
    fc.forEach((f) => {
      merged.push({
        year: f.year,
        cases: null,
        deaths: null,
        recoveries: null,
        predicted: f.predicted,
        actual: f.actual || f.predicted,
      })
    })
    return merged.sort((a, b) => a.year - b.year)
  }, [trendData, forecastTrendData, viewMode])

  const totalCases = filtered.reduce((s, c) => s + (Number(c.case_count) || 0), 0)
  const totalDeaths = filtered.reduce((s, c) => s + (Number(c.deaths) || 0), 0)
  const latestYear = trendData.length > 0 ? trendData[trendData.length - 1].year : '-'

  const forecastBoundary = useMemo(() => {
    if (forecastTrendData.length === 0) return null
    return Math.min(...forecastTrendData.map((f) => f.year))
  }, [forecastTrendData])

  const trendRefAreas = useMemo(() => {
    if (viewMode !== 'overlay' || !forecastBoundary) return []
    return [{ x1: forecastBoundary - 0.5, x2: forecastBoundary + 0.5, color: '#FBBF24', label: 'Forecast' }]
  }, [viewMode, forecastBoundary])

  const trendLines = useMemo(() => {
    if (viewMode === 'forecast') {
      return [
        { dataKey: 'predicted', name: 'Predicted Cases', color: '#0D7C66', strokeWidth: 2.5 },
        { dataKey: 'actual', name: 'Actual Cases', color: '#3B82F6', strokeWidth: 2 },
      ]
    }
    const noConnect = viewMode === 'overlay'
    const lines = [
      { dataKey: 'cases', name: 'Case Count', color: '#0D7C66', strokeWidth: 2.5, area: true, connectNulls: !noConnect },
      { dataKey: 'deaths', name: 'Deaths', color: '#EF4444', strokeWidth: 1.5, connectNulls: !noConnect },
    ]
    if (viewMode === 'overlay' && forecastTrendData.length > 0) {
      lines.push({
        dataKey: 'predicted', name: 'Forecast (ML)', color: '#FBBF24',
        strokeWidth: 2, dashed: true, dot: false,
      })
    }
    return lines
  }, [viewMode, forecastTrendData])

  const diseaseDist = useMemo(() => {
    const map = {}
    filtered.forEach((c) => {
      const name = c.disease_name
      if (isInvalidDisease(name)) return
      if (!map[name]) map[name] = 0
      map[name] += Number(c.case_count) || 0
    })
    return Object.entries(map)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [filtered])

  if (loading && cases.length === 0) {
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

  if (error && cases.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-dark-heading text-lg font-medium mb-2">Data Unavailable</h2>
        <p className="text-dark-text text-sm">Could not load trend data. API may be down.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-heading">Trends &amp; Forecasting</h1>
          <p className="text-dark-text text-sm mt-1">Historical patterns and ML-based predictions</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
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
        <div className="flex items-center gap-2 bg-dark-card border border-dark-border rounded-lg px-3 py-1.5">
          <Calendar className="w-4 h-4 text-dark-text" />
          <select
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="bg-transparent text-dark-heading text-sm focus:outline-none"
          >
            {regions.map((r) => (
              <option key={r} value={r} className="bg-dark-card">{r === 'all' ? 'All Regions' : shortName(r)}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1 bg-dark-card border border-dark-border rounded-lg p-0.5">
          {['overlay', 'historical', 'forecast'].map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                viewMode === mode ? 'bg-primary text-white' : 'text-dark-text hover:text-dark-heading'
              }`}
            >
              {mode === 'overlay' ? 'Combined' : mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard title="Total Cases (Filtered)" value={totalCases} subtitle={selectedDisease === 'all' ? 'All diseases' : selectedDisease} icon={TrendingUp} />
        <KPICard title="Total Deaths" value={totalDeaths} subtitle={selectedRegion === 'all' ? 'All regions' : shortName(selectedRegion)} icon={TrendingDown} color="red" />
        <KPICard title="Data Points" value={filtered.length} subtitle={`Latest: ${latestYear}`} color="blue" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-dark-heading mb-3">
            {viewMode === 'forecast' ? 'ML Forecast — GBT Regression' : viewMode === 'overlay' ? 'Historical + ML Forecast' : 'Annual Case Trends'}
          </h2>
          <TrendChart
            data={combinedData}
            lines={trendLines}
            height={400}
            referenceAreas={trendRefAreas}
          />
        </div>
        <div>
          <PieChartCard data={diseaseDist} title="Disease Distribution" height={360} />
        </div>
      </div>
    </div>
  )
}
