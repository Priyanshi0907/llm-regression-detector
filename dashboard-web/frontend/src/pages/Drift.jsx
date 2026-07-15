import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { ShieldCheck, AlertTriangle, Target, TrendingUp, TrendingDown } from 'lucide-react'
import { api } from '../api'
import MetricCard from '../components/MetricCard'
import TrendChart from '../components/TrendChart'
import { ChartSkeleton } from '../components/Skeleton'

const TABS = [
  { id: 'accuracy', label: 'Accuracy', key: 'overall_accuracy', color: '#5B7FFF', unit: '%' },
  { id: 'latency', label: 'Latency', key: 'avg_latency_ms', color: '#06B6D4', unit: 'ms' },
  { id: 'tokens', label: 'Token Usage', key: 'avg_tokens', color: '#A0AEC0', unit: '' },
  { id: 'quality', label: 'Summary Quality', key: 'avg_summary_relevance', color: '#22C55E', unit: '/5' },
]

export default function Drift() {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('accuracy')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.drift().then(setData).catch((e) => toast.error(`Failed to load drift data: ${e.message}`)).finally(() => setLoading(false))
  }, [])

  if (loading) return <ChartSkeleton height={400} />
  if (!data?.drift) {
    return (
      <div className="glass rounded-xl p-8 text-center text-gray-400">
        Need at least a few runs to compute a moving average. Currently have {data?.runs?.length ?? 0}.
      </div>
    )
  }

  const { drift, runs } = data
  const sortedRuns = [...runs].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  
  const uniqueVersionRuns = []
  const seenVersions = new Set()
  const reversedRuns = [...sortedRuns].reverse()
  for (const r of reversedRuns) {
    if (!seenVersions.has(r.prompt_version)) {
      seenVersions.add(r.prompt_version)
      uniqueVersionRuns.push(r)
    }
  }
  uniqueVersionRuns.reverse()

  const getVersionNum = (v) => {
    const m = v?.match(/\d+/)
    return m ? parseInt(m[0], 10) : 0
  }
  uniqueVersionRuns.sort((a, b) => getVersionNum(a.prompt_version) - getVersionNum(b.prompt_version))

  const window = drift?.window || 7
  const active = TABS.find((t) => t.id === tab)

  const withMovingAvg = uniqueVersionRuns.map((r, idx) => {
    const start = Math.max(0, idx - window + 1)
    const subset = uniqueVersionRuns.slice(start, idx + 1)
    const sum = subset.reduce((acc, curr) => acc + curr[active.key], 0)
    const moving_avg = sum / subset.length
    return {
      version: r.prompt_version,
      value: r[active.key],
      moving_avg: moving_avg,
      status: r.status,
    }
  })

  const chartData = withMovingAvg.map((item, idx) => ({
    index: idx,
    version: item.version,
    value: item.value,
    moving_avg: item.moving_avg,
    status: item.status,
  }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          icon={drift.is_drifting ? AlertTriangle : ShieldCheck}
          label="Drift Status"
          value={drift.is_drifting ? 'DRIFTING' : 'STABLE'}
          status={drift.is_drifting ? 'fail' : 'pass'}
          subtitle={drift.is_drifting ? 'Drift detected' : 'Performance stable'}
        />
        <MetricCard
          icon={Target}
          label="Current Moving Avg"
          value={`${drift.current_moving_avg.toFixed(1)}%`}
          status={drift.is_drifting ? 'fail' : 'pass'}
          subtitle={`Reference: ${drift.reference_avg.toFixed(1)}%`}
        />
        <MetricCard
          icon={drift.delta_pct >= 0 ? TrendingDown : TrendingUp}
          label="Delta vs Reference"
          value={`${drift.delta_pct >= 0 ? '+' : ''}${drift.delta_pct.toFixed(1)} pts`}
          trend={drift.is_drifting ? 'bad' : 'good'}
          status={drift.is_drifting ? 'fail' : 'pass'}
        />
      </div>
      <p className="text-sm text-gray-500">{drift.message}</p>

      <div className="flex gap-1 glass rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="glass rounded-xl p-4 fade-in-up space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Performance Drift Trend</span>
          <button
            onClick={() => {
              const headers = `version,${active.id},moving_avg,status\n`
              const rows = chartData.map(d => `${d.version},${d.value.toFixed(1)},${d.moving_avg.toFixed(1)},${d.status}`).join('\n')
              const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' })
              const url = URL.createObjectURL(blob)
              const link = document.createElement("a")
              link.setAttribute("href", url)
              link.setAttribute("download", `${active.id}_drift_trend_data.csv`)
              link.click()
            }}
            className="px-2 py-1 rounded border border-[#222938] hover:border-[#5B7FFF]/40 bg-[#0D1117] text-[10px] font-semibold text-[#A0AEC0] hover:text-white transition-colors cursor-pointer"
          >
            📥 Export CSV
          </button>
        </div>
        <TrendChart
          data={chartData}
          xKey="index"
          series={[
            { key: 'value', name: active.label, color: active.color },
            { key: 'moving_avg', name: `${window}-Run Moving Avg`, color: '#f59e0b', type: 'line', dashed: true }
          ]}
          unit={active.unit}
          height={360}
        />
      </div>
    </div>
  )
}
