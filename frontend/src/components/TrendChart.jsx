import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, ReferenceArea, Area, ComposedChart,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-3 shadow-xl">
      <p className="text-dark-heading text-sm font-medium mb-2">{label}</p>
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

export default function TrendChart({
  data, lines = [], xKey = 'year', height = 400,
  referenceAreas = [], referenceLines = [], type = 'line',
}) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-dark-card rounded-xl border border-dark-border">
        <p className="text-dark-text">No trend data available</p>
      </div>
    )
  }

  const colorPalette = ['#0D7C66', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

  const chartLines = lines.map((line, i) => (
    <Line
      key={line.dataKey || i}
      type="monotone"
      dataKey={line.dataKey}
      stroke={line.color || colorPalette[i % colorPalette.length]}
      strokeWidth={line.strokeWidth || 2}
      dot={line.dot !== false ? { r: 3, fill: line.color || colorPalette[i % colorPalette.length], strokeWidth: 0 } : false}
      activeDot={{ r: 5, fill: line.color || colorPalette[i % colorPalette.length], strokeWidth: 2, stroke: '#0F172A' }}
      name={line.name || line.dataKey}
      connectNulls={line.connectNulls !== false}
      strokeDasharray={line.dashed ? '5 3' : 'none'}
    />
  ))

  const chartAreas = lines
    .filter((l) => l.area)
    .map((line, i) => (
      <Area
        key={`area-${line.dataKey}`}
        type="monotone"
        dataKey={line.dataKey}
        stroke={line.color || colorPalette[i % colorPalette.length]}
        fill={line.color || colorPalette[i % colorPalette.length]}
        fillOpacity={0.1}
        strokeWidth={0}
      />
    ))

  return (
    <div className="bg-dark-card rounded-xl border border-dark-border p-5">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
          <XAxis
            dataKey={xKey}
            stroke="#94A3B8"
            tick={{ fill: '#94A3B8', fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            stroke="#94A3B8"
            tick={{ fill: '#94A3B8', fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
            tickFormatter={(v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: 16 }}
            formatter={(value) => <span className="text-dark-text text-xs">{value}</span>}
          />
          {referenceAreas.map((area, i) => (
            <ReferenceArea
              key={i}
              x1={area.x1}
              x2={area.x2}
              fill={area.color || '#3B82F6'}
              fillOpacity={0.08}
              label={area.label ? { value: area.label, position: 'insideTopRight', fill: '#94A3B8', fontSize: 11 } : undefined}
            />
          ))}
          {referenceLines.map((line, i) => (
            <ReferenceLine
              key={i}
              y={line.y}
              stroke={line.color || '#F59E0B'}
              strokeDasharray="4 4"
              label={line.label ? { value: line.label, position: 'right', fill: '#94A3B8', fontSize: 11 } : undefined}
            />
          ))}
          {chartAreas}
          {chartLines}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
