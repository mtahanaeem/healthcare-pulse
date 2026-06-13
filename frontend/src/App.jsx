import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Trends from './pages/Trends'
import RegionalMap from './pages/RegionalMap'
import Explorer from './pages/Explorer'
import PipelineMonitor from './pages/PipelineMonitor'

export default function App() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-dark-bg">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <main className={`flex-1 overflow-y-auto transition-all duration-300 ${collapsed ? 'ml-16' : 'ml-64'}`}>
        <div className="p-6 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/regional" element={<RegionalMap />} />
            <Route path="/explorer" element={<Explorer />} />
            <Route path="/pipeline" element={<PipelineMonitor />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
