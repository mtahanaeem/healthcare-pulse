import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  LayoutDashboard, TrendingUp, Map, Search, Activity,
  ChevronLeft, ChevronRight, HeartPulse, RefreshCw,
  CheckCircle, XCircle, Clock,
} from 'lucide-react'

const API = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '' })

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/trends', label: 'Trends', icon: TrendingUp },
  { path: '/regional', label: 'Regional Map', icon: Map },
  { path: '/explorer', label: 'Explorer', icon: Search },
  { path: '/pipeline', label: 'Pipeline', icon: Activity },
]

export default function Sidebar({ collapsed, onToggle }) {
  const [pipelineStatus, setPipelineStatus] = useState(null)

  useEffect(() => {
    let mounted = true
    async function fetchStatus() {
      try {
        const { data } = await API.get('/api/pipeline/status')
        if (mounted) setPipelineStatus(data)
      } catch { /* ignore */ }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  const stages = pipelineStatus?.pipeline_stages || {}
  const stageValues = Object.values(stages)
  const running = stageValues.some((s) => s?.status === 'running')
  const failed = stageValues.some((s) => s?.status === 'failed')
  const allCompleted = stageValues.length > 0 && stageValues.every((s) => s?.status === 'completed')
  const anyCompleted = stageValues.some((s) => s?.status === 'completed')

  let statusIcon = <Clock className="w-3.5 h-3.5 text-dark-text" />
  let statusText = 'Idle'
  let statusColor = 'text-dark-text'

  if (running) { statusIcon = <RefreshCw className="w-3.5 h-3.5 text-primary animate-spin" />; statusText = 'Running'; statusColor = 'text-primary' }
  else if (failed) { statusIcon = <XCircle className="w-3.5 h-3.5 text-red-400" />; statusText = 'Failed'; statusColor = 'text-red-400' }
  else if (allCompleted) { statusIcon = <CheckCircle className="w-3.5 h-3.5 text-green-400" />; statusText = 'Completed'; statusColor = 'text-green-400' }
  else if (anyCompleted) { statusIcon = <CheckCircle className="w-3.5 h-3.5 text-green-400/60" />; statusText = 'Partial'; statusColor = 'text-green-400/60' }

  return (
    <aside className={`fixed left-0 top-0 h-full bg-dark-card border-r border-dark-border z-50 transition-all duration-300 flex flex-col ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className="flex items-center gap-3 px-4 h-16 border-b border-dark-border">
        <HeartPulse className="w-8 h-8 text-primary flex-shrink-0" />
        {!collapsed && (
          <div className="flex flex-col">
            <span className="text-dark-heading font-semibold text-sm leading-tight">Health Pipeline</span>
            <span className="text-dark-text text-xs">Surveillance Dashboard</span>
          </div>
        )}
      </div>

      <nav className="flex-1 py-4 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path} to={item.path} end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'text-dark-text hover:bg-dark-border/50 hover:text-dark-heading border border-transparent'
              }`
            }
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {!collapsed && (
        <div className="px-4 py-3 border-t border-dark-border">
          <div className={`flex items-center gap-2 text-xs ${statusColor}`}>
            {statusIcon}
            <span>Pipeline: {statusText}</span>
          </div>
        </div>
      )}

      <button onClick={onToggle} className="flex items-center justify-center h-12 border-t border-dark-border text-dark-text hover:text-dark-heading hover:bg-dark-border/30 transition-colors">
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
  )
}
