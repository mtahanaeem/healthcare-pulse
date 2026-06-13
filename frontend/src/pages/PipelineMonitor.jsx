import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Play,
  StopCircle,
  ChevronRight,
  AlertTriangle,
  Server,
  Database,
  Cpu,
  BarChart3,
  LayoutDashboard,
} from 'lucide-react'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

const STAGES = [
  { key: 'extract', label: 'EXTRACT', description: 'WHO / OWID / CDC Data Ingestion', icon: Database, color: '#3B82F6' },
  { key: 'etl', label: 'ETL', description: 'Pentaho Kettle Transformation', icon: Server, color: '#8B5CF6' },
  { key: 'clean', label: 'CLEAN', description: 'PySpark Data Cleaning', icon: Cpu, color: '#0D7C66' },
  { key: 'warehouse', label: 'WAREHOUSE', description: 'PostgreSQL Star Schema Load', icon: Database, color: '#F59E0B' },
  { key: 'ml', label: 'ML', description: 'GBT Regression Forecasting', icon: BarChart3, color: '#EC4899' },
  { key: 'dashboard', label: 'DASHBOARD', description: 'React Visualization Layer', icon: LayoutDashboard, color: '#22C55E' },
]

function StatusIcon({ status }) {
  if (status === 'completed') return <CheckCircle className="w-5 h-5 text-green-400" />
  if (status === 'running') return <RefreshCw className="w-5 h-5 text-primary animate-spin" />
  if (status === 'failed') return <XCircle className="w-5 h-5 text-red-400" />
  return <Clock className="w-5 h-5 text-dark-text" />
}

function StageCard({ stage, status }) {
  const Icon = stage.icon
  return (
    <div className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
      status === 'running'
        ? 'bg-primary/10 border-primary/40'
        : status === 'completed'
        ? 'bg-green-500/5 border-green-500/20'
        : status === 'failed'
        ? 'bg-red-500/5 border-red-500/20'
        : 'bg-dark-card border-dark-border'
    }`}>
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0`} style={{ backgroundColor: `${stage.color}20` }}>
        <Icon className="w-5 h-5" style={{ color: stage.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-dark-heading">{stage.label}</span>
          <StatusIcon status={status} />
        </div>
        <p className="text-xs text-dark-text truncate">{stage.description}</p>
        {status === 'running' && (
          <div className="mt-2 h-1 bg-dark-border rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function PipelineMonitor() {
  const [pipelineData, setPipelineData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [knimeOutput, setKnimeOutput] = useState(null)
  const [knimeLoading, setKnimeLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await API.get('/api/pipeline/status')
      setPipelineData(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  async function handleRunKnime() {
    setKnimeLoading(true)
    setKnimeOutput(null)
    try {
      const { data } = await API.post(
        '/api/run-knime',
        {},
        {
          headers: {
            'X-API-Key': import.meta.env.VITE_API_KEY || 'hc-pipeline-api-key-2026',
          },
          timeout: 300000,
        }
      )
      setKnimeOutput(data)
      fetchStatus()
    } catch (err) {
      setKnimeOutput({
        status: 'failed',
        error: err.response?.data?.error || err.message,
        timestamp: new Date().toISOString(),
      })
    } finally {
      setKnimeLoading(false)
    }
  }

  const pipelineStages = pipelineData?.pipeline_stages || {}
  const knimeRunning = pipelineData?.knime_running || false

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-heading">Pipeline Monitor</h1>
          <p className="text-dark-text text-sm mt-1">Real-time orchestration lifecycle tracking</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchStatus}
            className="flex items-center gap-2 px-3 py-2 text-xs text-dark-text border border-dark-border rounded-lg hover:border-primary/30 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={handleRunKnime}
            disabled={knimeLoading || knimeRunning}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              knimeLoading || knimeRunning
                ? 'bg-dark-border text-dark-text cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary/80'
            }`}
          >
            {knimeLoading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            {knimeLoading ? 'Running...' : knimeRunning ? 'In Progress' : 'Run KNIME ETL'}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Connection Error</p>
            <p className="text-xs text-red-200/70">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {STAGES.map((stage, index) => (
          <div key={stage.key} className="relative">
            <StageCard
              stage={stage}
              status={pipelineStages[stage.key]?.status || 'idle'}
            />
            {index < STAGES.length - 1 && (
              <div className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 z-10">
                <ChevronRight className="w-4 h-4 text-dark-border" />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-dark-card rounded-xl border border-dark-border p-5">
          <h2 className="text-lg font-semibold text-dark-heading mb-4">KNIME Execution Gateway</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-dark-text">Status</span>
              <span className={`flex items-center gap-1.5 ${
                knimeRunning ? 'text-primary' : knimeOutput?.status === 'completed' ? 'text-green-400' : 'text-dark-text'
              }`}>
                {knimeRunning ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Running
                  </>
                ) : knimeOutput?.status === 'completed' ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5" />
                    Completed
                  </>
                ) : knimeOutput?.status === 'failed' ? (
                  <>
                    <XCircle className="w-3.5 h-3.5" />
                    Failed
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5" />
                    Idle
                  </>
                )}
              </span>
            </div>
            {knimeOutput?.execution_time_seconds && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-dark-text">Duration</span>
                <span className="text-dark-heading">{knimeOutput.execution_time_seconds}s</span>
              </div>
            )}
            {knimeOutput?.exit_code !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-dark-text">Exit Code</span>
                <span className={`font-mono ${knimeOutput.exit_code === 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {knimeOutput.exit_code}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-dark-card rounded-xl border border-dark-border p-5">
          <h2 className="text-lg font-semibold text-dark-heading mb-4">Pipeline State</h2>
          <div className="space-y-2">
            {STAGES.map((stage) => {
              const s = pipelineStages[stage.key] || { status: 'idle', last_run: null }
              return (
                <div key={stage.key} className="flex items-center justify-between text-sm py-1.5 border-b border-dark-border/30 last:border-0">
                  <div className="flex items-center gap-2">
                    <StatusIcon status={s.status} />
                    <span className="text-dark-text">{stage.label}</span>
                  </div>
                  <span className={`text-xs ${
                    s.status === 'completed' ? 'text-green-400' :
                    s.status === 'running' ? 'text-primary' :
                    s.status === 'failed' ? 'text-red-400' : 'text-dark-text/50'
                  }`}>
                    {s.status === 'idle' ? '—' : s.status}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {knimeOutput && (
        <div className="bg-dark-card rounded-xl border border-dark-border p-5">
          <h2 className="text-lg font-semibold text-dark-heading mb-3">Last KNIME Run Output</h2>
          <pre className="bg-dark-bg rounded-lg p-4 text-xs font-mono text-dark-text overflow-x-auto max-h-64 overflow-y-auto">
            {JSON.stringify(knimeOutput, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
