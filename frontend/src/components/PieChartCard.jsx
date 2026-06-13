import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { shortName } from '../utils/countryMapping'

const MIN_PCT = 2

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null
  const entry = payload[0]
  const total = entry.payload._total || 1
  const pct = ((entry.value / total) * 100).toFixed(1)
  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-3 shadow-xl">
      <p className="text-dark-heading text-sm font-medium mb-1">{shortName(entry.name)}</p>
      <p className="text-dark-text text-xs">{Number(entry.value).toLocaleString()} ({pct}%)</p>
    </div>
  )
}

const COLORS = ['#0D7C66', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#94A3B8']

function groupSmallSlices(items, minPct) {
  if (items.length <= 1) return items
  const total = items.reduce((s, d) => s + (Number(d.value) || 0), 0)
  const threshold = total * (minPct / 100)
  const main = []
  let otherSum = 0
  for (const d of items) {
    const v = Number(d.value) || 0
    if (v >= threshold) {
      main.push(d)
    } else {
      otherSum += v
    }
  }
  if (otherSum > 0) {
    main.push({ name: 'Other', value: otherSum })
  }
  return main
}

export default function PieChartCard({ data = [], title, height = 360, innerRadius = 70, outerRadius = 100, minPct = MIN_PCT }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-dark-card rounded-xl border border-dark-border p-5">
        {title && <h3 className="text-sm font-semibold text-dark-heading mb-4">{title}</h3>}
        <div className="flex items-center justify-center h-64">
          <p className="text-dark-text">No data available</p>
        </div>
      </div>
    )
  }

  const sorted = [...data].sort((a, b) => (Number(b.value) || 0) - (Number(a.value) || 0))
  const grouped = groupSmallSlices(sorted, minPct)
  const total = grouped.reduce((s, d) => s + (Number(d.value) || 0), 0)
  const withTotal = grouped.map((d) => ({ ...d, _total: total }))

  return (
    <div className="bg-dark-card rounded-xl border border-dark-border p-5">
      {title && (
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-dark-heading">{title}</h3>
          <span className="text-xs text-dark-text">{total.toLocaleString()} total</span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={withTotal}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
            animationDuration={800}
            animationEasing="ease-out"
          >
            {withTotal.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: 16 }}
            formatter={(value) => <span className="text-dark-text text-xs">{shortName(value)}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
