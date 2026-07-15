import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, TrendingUp, ShieldCheck, Activity } from 'lucide-react'
import { api } from '../api'
import Badge from '../components/Badge'
import MetricCard from '../components/MetricCard'
import { RowSkeleton } from '../components/Skeleton'

function CompareRow({ label, before, after, fmt = (v) => v.toFixed(1), higherIsBetter = true }) {
  const delta = after - before
  const positive = higherIsBetter ? delta >= 0 : delta <= 0
  const arrow = delta > 0 ? '↑' : delta < 0 ? '↓' : '→'
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/5 text-sm">
      <div className="text-gray-500">{label}</div>
      <div className="flex items-center gap-2">
        <span className="font-semibold text-gray-200">{fmt(before)}</span>
        <span className="text-gray-600">→</span>
        <span className="font-semibold text-gray-200">{fmt(after)}</span>
        {delta !== 0 && (
          <span className={`font-bold ml-1 ${positive ? 'text-emerald-400' : 'text-red-400'}`}>
            {arrow} {fmt(Math.abs(delta))}
          </span>
        )}
      </div>
    </div>
  )
}

const METRIC_ROWS = [
  { label: 'Provider', key: (r) => r.provider, isText: true },
  { label: 'Accuracy', key: (r) => r.overall_accuracy, fmt: (v) => `${v.toFixed(1)}%`, best: 'max' },
  { label: 'Avg Latency', key: (r) => r.avg_latency_ms, fmt: (v) => `${v.toFixed(0)}ms`, best: 'min' },
  { label: 'Avg Tokens', key: (r) => r.avg_tokens, fmt: (v) => v.toFixed(0), best: 'min' },
  { label: 'Avg Cost/run', key: (r) => r.avg_cost_usd, fmt: (v) => `$${v.toFixed(4)}`, best: 'min' },
  { label: 'Summary Relevance', key: (r) => r.avg_summary_relevance, fmt: (v) => `${v.toFixed(1)}/5`, best: 'max' },
  { label: 'Regressions', key: (r) => r.regressions, fmt: (v) => v, best: 'min' },
]

export default function Compare() {
  const [runs, setRuns] = useState([])
  const [mode, setMode] = useState('diff') // 'diff' | 'sideBySide'
  const [loading, setLoading] = useState(true)

  // 2-way diff mode state
  const [leftId, setLeftId] = useState(null)
  const [rightId, setRightId] = useState(null)
  const [cmp, setCmp] = useState(null)

  // N-way side-by-side mode state
  const [selectedIds, setSelectedIds] = useState([])
  const [multiResult, setMultiResult] = useState(null)

  useEffect(() => {
    api.runs().then((rs) => {
      setRuns(rs)
      if (rs.length > 1) {
        setLeftId(rs[1].run_id)
        setRightId(rs[0].run_id)
        setSelectedIds(rs.slice(0, Math.min(3, rs.length)).map((r) => r.run_id))
      } else if (rs[0]) {
        setLeftId(rs[0].run_id)
        setRightId(rs[0].run_id)
        setSelectedIds([rs[0].run_id])
      }
    }).catch((e) => toast.error(`Failed to load runs: ${e.message}`)).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (mode !== 'diff' || !leftId || !rightId) return
    api.compare(leftId, rightId).then(setCmp).catch((e) => toast.error(`Compare failed: ${e.message}`))
  }, [mode, leftId, rightId])

  useEffect(() => {
    if (mode !== 'sideBySide' || selectedIds.length < 2) return
    api.compareMulti(selectedIds).then(setMultiResult).catch((e) => toast.error(`Compare failed: ${e.message}`))
  }, [mode, selectedIds])

  const categories = useMemo(() => {
    if (!cmp) return []
    return [...new Set([...Object.keys(cmp.run_a.category_accuracy), ...Object.keys(cmp.run_b.category_accuracy)])].sort()
  }, [cmp])

  function toggleSelected(id) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  function bestValue(rows, getter, best) {
    const values = rows.map(getter)
    return best === 'max' ? Math.max(...values) : Math.min(...values)
  }

  if (loading) return <RowSkeleton rows={6} />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <p className="text-sm text-gray-500">
          {mode === 'diff'
            ? 'Head-to-head diff with deltas — best for before/after on a single prompt change.'
            : 'Side-by-side table — best for comparing multiple providers or versions at once.'}
        </p>
        <div className="flex gap-1 glass rounded-xl p-1">
          <button
            onClick={() => setMode('diff')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${mode === 'diff' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500 hover:text-gray-300'}`}
          >
            2-Way Diff
          </button>
          <button
            onClick={() => setMode('sideBySide')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${mode === 'sideBySide' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500 hover:text-gray-300'}`}
          >
            Side-by-Side (N-way)
          </button>
        </div>
      </div>

      {mode === 'diff' ? (
        <>
          <div className="flex flex-wrap gap-4">
            <select value={leftId ?? ''} onChange={(e) => setLeftId(e.target.value)} className="glass rounded-lg px-3 py-2 text-sm outline-none flex-1 min-w-[220px]">
              {runs.map((r) => <option key={r.run_id} value={r.run_id} className="bg-[#12141c]">Run A (before): {r.prompt_version} · {r.provider} · {r.run_id}</option>)}
            </select>
            <select value={rightId ?? ''} onChange={(e) => setRightId(e.target.value)} className="glass rounded-lg px-3 py-2 text-sm outline-none flex-1 min-w-[220px]">
              {runs.map((r) => <option key={r.run_id} value={r.run_id} className="bg-[#12141c]">Run B (after): {r.prompt_version} · {r.provider} · {r.run_id}</option>)}
            </select>
          </div>

          {cmp && (
            <>
              <div className="flex items-center gap-2">
                <Badge variant="version">{cmp.run_a.prompt_version} · {cmp.run_a.provider}</Badge>
                <span className="text-gray-500">→</span>
                <Badge variant="version">{cmp.run_b.prompt_version} · {cmp.run_b.provider}</Badge>
              </div>

              <div className="glass rounded-xl p-5 fade-in-up">
                <CompareRow label="Accuracy" before={cmp.run_a.overall_accuracy} after={cmp.run_b.overall_accuracy} fmt={(v) => `${v.toFixed(1)}%`} />
                <CompareRow label="Avg Latency" before={cmp.run_a.avg_latency_ms} after={cmp.run_b.avg_latency_ms} fmt={(v) => `${v.toFixed(0)}ms`} higherIsBetter={false} />
                <CompareRow label="Avg Tokens" before={cmp.run_a.avg_tokens} after={cmp.run_b.avg_tokens} fmt={(v) => v.toFixed(0)} higherIsBetter={false} />
                <CompareRow label="Avg Cost/run" before={cmp.run_a.avg_cost_usd} after={cmp.run_b.avg_cost_usd} fmt={(v) => `$${v.toFixed(4)}`} higherIsBetter={false} />
                <CompareRow label="Summary Relevance" before={cmp.run_a.avg_summary_relevance} after={cmp.run_b.avg_summary_relevance} fmt={(v) => `${v.toFixed(1)}/5`} />
                {categories.map((cat) => (
                  <CompareRow
                    key={cat}
                    label={`${cat[0].toUpperCase()}${cat.slice(1)} accuracy`}
                    before={cmp.run_a.category_accuracy[cat] ?? 0}
                    after={cmp.run_b.category_accuracy[cat] ?? 0}
                    fmt={(v) => `${v.toFixed(0)}%`}
                  />
                ))}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <MetricCard
                  icon={AlertTriangle}
                  label="Regressions (A→B)"
                  value={cmp.regressions}
                  status={cmp.regressions > 0 ? 'fail' : 'pass'}
                  trend={cmp.regressions > 0 ? 'bad' : 'good'}
                />
                <MetricCard
                  icon={TrendingUp}
                  label="Improvements (A→B)"
                  value={cmp.improvements}
                  status={cmp.improvements > 0 ? 'pass' : 'neutral'}
                  trend={cmp.improvements > 0 ? 'good' : 'neutral'}
                />
                <MetricCard
                  icon={cmp.statistically_significant ? ShieldCheck : Activity}
                  label="Statistically Significant"
                  value={cmp.statistically_significant ? 'Yes' : 'No'}
                  delta={cmp.p_value != null ? `p = ${cmp.p_value.toFixed(3)}` : null}
                  status={cmp.statistically_significant ? 'pass' : 'neutral'}
                  trend={cmp.statistically_significant ? 'good' : 'neutral'}
                />
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="glass rounded-xl p-4">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-3">Select runs to compare (2+)</div>
            <div className="flex flex-wrap gap-2">
              {runs.slice(0, 20).map((r) => (
                <button
                  key={r.run_id}
                  onClick={() => toggleSelected(r.run_id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    selectedIds.includes(r.run_id)
                      ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300'
                      : 'border-white/10 text-gray-400 hover:border-white/25'
                  }`}
                >
                  {r.provider} · {r.prompt_version}
                </button>
              ))}
            </div>
          </div>

          {multiResult && multiResult.runs.length >= 2 && (
            <div className="glass rounded-xl overflow-hidden fade-in-up">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left px-4 py-3 text-xs text-gray-500 uppercase sticky left-0 bg-[#12141c]">Metric</th>
                      {multiResult.runs.map((r) => (
                        <th key={r.run_id} className="text-left px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <Badge variant="version">{r.provider}</Badge>
                            <span className="text-xs text-gray-500">{r.prompt_version}</span>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {METRIC_ROWS.map((row) => {
                      const isBest = row.best && !row.isText
                        ? bestValue(multiResult.runs, row.key, row.best)
                        : null
                      return (
                        <tr key={row.label} className="border-t border-white/5">
                          <td className="px-4 py-2.5 text-gray-500 sticky left-0 bg-[#12141c]">{row.label}</td>
                          {multiResult.runs.map((r) => {
                            const val = row.key(r)
                            const isWinner = isBest !== null && val === isBest
                            return (
                              <td key={r.run_id} className={`px-4 py-2.5 ${isWinner ? 'text-emerald-400 font-bold' : 'text-gray-200'}`}>
                                {row.fmt ? row.fmt(val) : val} {isWinner && '🏆'}
                              </td>
                            )
                          })}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
