import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

function TrendArrow({ value }) {
  if (value > 0) return <TrendingUp className="w-4 h-4 text-green-400" />
  if (value < 0) return <TrendingDown className="w-4 h-4 text-red-400" />
  return <Minus className="w-4 h-4 text-dark-text" />
}

export default function KPICard({ title, value, subtitle, trend, loading, icon: Icon, color = 'primary' }) {
  if (loading) {
    return (
      <div className="bg-dark-card rounded-xl border border-dark-border p-5 animate-pulse">
        <div className="flex items-start justify-between">
          <div className="space-y-3 flex-1">
            <div className="h-4 bg-dark-border rounded w-24" />
            <div className="h-8 bg-dark-border rounded w-32" />
            <div className="h-3 bg-dark-border rounded w-20" />
          </div>
          <div className="w-10 h-10 bg-dark-border rounded-lg" />
        </div>
      </div>
    )
  }

  const colorMap = {
    primary: 'bg-primary/20 text-primary',
    green: 'bg-green-500/20 text-green-400',
    red: 'bg-red-500/20 text-red-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    blue: 'bg-blue-500/20 text-blue-400',
  }

  return (
    <div className="bg-dark-card rounded-xl border border-dark-border p-5 hover:border-primary/30 transition-all duration-200">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-dark-text text-sm font-medium">{title}</p>
          <p className="text-dark-heading text-3xl font-bold tracking-tight">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {subtitle && (
            <div className="flex items-center gap-2">
              {trend !== undefined && <TrendArrow value={trend} />}
              <p className={`text-xs ${trend > 0 ? 'text-green-400' : trend < 0 ? 'text-red-400' : 'text-dark-text'}`}>
                {subtitle}
              </p>
            </div>
          )}
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorMap[color] || colorMap.primary}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  )
}
