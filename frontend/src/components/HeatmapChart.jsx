import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { shortName } from '../utils/countryMapping'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-3 shadow-xl">
      <p className="text-dark-heading text-sm font-medium mb-2">{shortName(label)}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-dark-text">{entry.name}:</span>
          <span className="text-dark-heading font-medium">{Number(entry.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

function getBarColor(value, maxValue) {
  const ratio = value / maxValue
  if (ratio > 0.8) return '#EF4444'
  if (ratio > 0.6) return '#F59E0B'
  if (ratio > 0.4) return '#0D7C66'
  if (ratio > 0.2) return '#0a6351'
  return '#074a3d'
}

export default function HeatmapChart({ data, xKey = 'name', valueKey = 'value', height = 500, colorBy = 'value', shortenLabels = true }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-dark-card rounded-xl border border-dark-border">
        <p className="text-dark-text">No data available</p>
      </div>
    )
  }

  const maxValue = Math.max(...data.map((d) => Number(d[valueKey]) || 0))
  const processed = data.map((d) => ({
    ...d,
    displayName: shortenLabels ? shortName(d[xKey]) : d[xKey],
  }))

  return (
    <div className="bg-dark-card rounded-xl border border-dark-border p-5">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={processed}
          layout="vertical"
          margin={{ top: 10, right: 60, left: 120, bottom: 10 }}
          barCategoryGap="20%"
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} horizontal={false} />
          <XAxis
            type="number"
            stroke="#94A3B8"
            tick={{ fill: '#94A3B8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
            tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(v >= 1000000 ? 1 : 0)}${v >= 1000000 ? 'M' : 'k'}` : v}
          />
          <YAxis
            type="category"
            dataKey="displayName"
            stroke="#94A3B8"
            tick={{ fill: '#94A3B8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
            width={120}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey={valueKey} radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={true} animationDuration={800} animationEasing="ease-out">
            {processed.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={colorBy === 'value' ? getBarColor(Number(entry[valueKey]) || 0, maxValue) : entry.color || '#0D7C66'}
              />
            ))}
            <LabelList
              dataKey={valueKey}
              position="right"
              style={{ fill: '#94A3B8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
              formatter={(v) => Number(v).toLocaleString()}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
