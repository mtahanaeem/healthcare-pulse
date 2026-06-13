import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import {
  Activity, Skull, HeartPulse, Globe, TrendingUp, AlertTriangle, Pill, MapPin,
} from 'lucide-react'
import KPICard from '../components/KPICard'
import TrendChart from '../components/TrendChart'
import HeatmapChart from '../components/HeatmapChart'
import PieChartCard from '../components/PieChartCard'
import DataTable from '../components/DataTable'
import { shortName, isInvalidDisease, isCleanRecord } from '../utils/countryMapping'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    async function fetchAll() {
      try {
        const [metricsRes, casesRes] = await Promise.all([
          API.get('/api/metrics'),
          API.get('/api/cases', { params: { per_page: 100, sort_by: 'loaded_at', sort_order: 'desc' } }),
        ])
        if (mounted) {
          setMetrics(metricsRes.data)
          setCases(casesRes.data.data || [])
        }
      } catch (err) {
        if (mounted) setError(err.message)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchAll()
    const interval = setInterval(fetchAll, 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  const validCases = useMemo(() => {
    return (cases || []).filter((c) => isCleanRecord(c))
  }, [cases])

  const diseaseData = useMemo(() => {
    return (metrics?.cases_by_disease || [])
      .filter((d) => !isInvalidDisease(d.disease_name))
      .map((d) => ({
        name: d.disease_name,
        value: Number(d.total_cases),
      }))
      .sort((a, b) => b.value - a.value)
  }, [metrics])

  const regionData = useMemo(() => {
    return (metrics?.cases_by_region || [])
      .map((r) => ({
        name: r.region_name,
        value: Number(r.total_cases),
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 30)
  }, [metrics])

  const totalCases = useMemo(() => {
    return diseaseData.reduce((s, d) => s + d.value, 0)
  }, [diseaseData])

  const tableColumns = [
    { key: 'disease_name', label: 'Disease', width: '18%' },
    { key: 'region_name', label: 'Region', width: '14%', render: (v) => shortName(v) },
    { key: 'year', label: 'Year', width: '8%', format: 'number' },
    { key: 'case_count', label: 'Cases', width: '12%', format: 'number' },
    { key: 'cases_per_100k', label: 'Per 100k', width: '10%', format: 'decimal' },
    { key: 'deaths', label: 'Deaths', width: '10%', format: 'number' },
    { key: 'source', label: 'Source', width: '10%' },
  ]

  const topRegions = useMemo(() => {
    return regionData.slice(0, 5).map((r) => ({ name: shortName(r.name), value: r.value }))
  }, [regionData])

  const kpiCases = totalCases || metrics?.total_cases || 0
  const kpiDeaths = metrics?.total_deaths || 0
  const kpiRecoveries = metrics?.total_recoveries || 0
  const kpiRegions = metrics?.regions_covered || 0
  const kpiDiseases = metrics?.active_diseases || diseaseData.length || 0

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-7 bg-dark-border rounded w-48 animate-pulse mb-2" />
            <div className="h-4 bg-dark-border rounded w-64 animate-pulse" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-dark-card rounded-xl border border-dark-border p-5 animate-pulse">
              <div className="h-4 bg-dark-border rounded w-24 mb-3" />
              <div className="h-8 bg-dark-border rounded w-32 mb-2" />
              <div className="h-3 bg-dark-border rounded w-20" />
            </div>
          ))}
        </div>
        <div className="h-80 bg-dark-card rounded-xl border border-dark-border animate-pulse" />
      </div>
    )
  }

  if (error && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-dark-heading text-lg font-medium mb-2">Connection Error</h2>
        <p className="text-dark-text text-sm">Could not connect to the API at /api/metrics</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/80 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-heading">Dashboard</h1>
          <p className="text-dark-text text-sm mt-1">
            Disease surveillance overview &middot; {kpiRegions} regions tracked &middot; {kpiDiseases} diseases
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-dark-text bg-dark-card px-3 py-1.5 rounded-lg border border-dark-border">
          <Activity className="w-3.5 h-3.5 text-primary" />
          Auto-refreshing
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Total Cases" value={kpiCases} subtitle="Across all diseases and regions" icon={HeartPulse} color="primary" />
        <KPICard title="Total Deaths" value={kpiDeaths} subtitle={`${kpiRegions} regions affected`} icon={Skull} color="red" />
        <KPICard title="Total Recoveries" value={kpiRecoveries} subtitle={`${kpiDiseases} active diseases`} icon={Pill} color="green" />
        <KPICard title="Regions Covered" value={kpiRegions} subtitle={`Since ${metrics?.date_range?.min || 'N/A'}`} icon={Globe} color="blue" />
      </div>

      {topRegions.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-dark-heading mb-3 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" /> Top 5 Countries
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {topRegions.map((r, i) => (
              <div key={i} className="bg-dark-card border border-dark-border rounded-lg px-4 py-3 hover:border-primary/30 transition-all">
                <p className="text-dark-text text-xs font-medium mb-1">{i + 1}. {r.name}</p>
                <p className="text-dark-heading text-lg font-bold">{r.value.toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-dark-heading mb-3">Cases by Region</h2>
          <HeatmapChart
            data={regionData}
            xKey="name"
            valueKey="value"
            height={Math.max(400, regionData.length * 22)}
            shortenLabels={true}
          />
        </div>
        <div>
          <PieChartCard
            data={diseaseData}
            title="Disease Distribution"
            height={360}
          />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-dark-heading mb-3">Recent Cases</h2>
        <DataTable
          columns={tableColumns}
          data={validCases}
          loading={loading}
          pageSize={15}
          searchable={true}
        />
      </div>
    </div>
  )
}
