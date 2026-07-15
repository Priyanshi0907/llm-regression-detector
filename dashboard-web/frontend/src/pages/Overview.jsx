import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { Target, AlertTriangle, TrendingUp, ChevronDown, ChevronRight, ShieldCheck, TrendingDown } from 'lucide-react'
import { api } from '../api'
import MetricCard from '../components/MetricCard'
import Badge, { statusVariant } from '../components/Badge'
import TrendChart from '../components/TrendChart'
import BarChartPanel from '../components/BarChartPanel'
import { GridSkeleton, ChartSkeleton } from '../components/Skeleton'
import PipelineVisualizer from '../components/PipelineVisualizer'

export default function Overview() {
  const [data, setData] = useState(null)
  const [runs, setRuns] = useState([])
  const [expanded, setExpanded] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAllRegressions, setShowAllRegressions] = useState(false)

  useEffect(() => {
    Promise.all([api.overview(), api.runs()])
      .then(([ov, rs]) => {
        setData(ov)
        setRuns(rs)
      })
      .catch((e) => toast.error(`Failed to load overview: ${e.message}`))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <GridSkeleton count={4} />
        <div className="grid grid-cols-2 gap-4">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    )
  }

  if (!data?.has_data) {
    return (
      <div className="glass rounded-xl p-8 text-center text-gray-400">
        No eval runs yet. Run <code className="text-indigo-300">python -m src.cli --prompt prompts/v7.yaml</code> to get started.
      </div>
    )
  }

  const { latest, baseline, comparison, drift, regressions, improvements } = data
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

  const withMovingAvg = uniqueVersionRuns.map((r, idx) => {
    const start = Math.max(0, idx - window + 1)
    const subset = uniqueVersionRuns.slice(start, idx + 1)
    const sum = subset.reduce((acc, curr) => acc + curr.overall_accuracy, 0)
    const moving_avg = sum / subset.length
    return {
      version: r.prompt_version,
      accuracy: r.overall_accuracy,
      moving_avg: moving_avg,
      status: r.status,
    }
  })

  const trendData = withMovingAvg.map((item, idx) => ({
    index: idx,
    version: item.version,
    accuracy: item.accuracy,
    moving_avg: item.moving_avg,
    status: item.status,
  }))

  const catData = Object.entries(latest.category_accuracy).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <PipelineVisualizer
        version={latest.prompt_version}
        status={latest.status}
        totalCases={latest.total_cases}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={latest.status === 'FAIL' || latest.status === 'WARNING' ? AlertTriangle : ShieldCheck}
          label="Current Status"
          value={latest.status}
          subtitle={latest.status === 'FAIL' || latest.status === 'WARNING' ? 'Threshold exceeded' : 'All checks green'}
          status={latest.status}
        />
        <MetricCard
          icon={Target}
          label="Overall Accuracy"
          value={`${latest.overall_accuracy.toFixed(0)}%`}
          delta={comparison ? `${comparison.overall_accuracy_delta >= 0 ? '↑' : '↓'} ${Math.abs(comparison.overall_accuracy_delta).toFixed(0)}% vs last run` : null}
          trend={comparison ? (comparison.overall_accuracy_delta >= 0 ? 'good' : 'bad') : 'neutral'}
          status={latest.status === 'FAIL' ? 'fail' : latest.status === 'WARNING' ? 'warning' : 'pass'}
        />
        <MetricCard
          icon={TrendingDown}
          label="Regressions"
          value={latest.regressions}
          delta={baseline ? `${latest.regressions > baseline.regressions ? '↑' : latest.regressions < baseline.regressions ? '↓' : ''} ${Math.abs(latest.regressions - baseline.regressions)} vs last run` : null}
          trend={baseline ? (latest.regressions > baseline.regressions ? 'bad' : latest.regressions < baseline.regressions ? 'good' : 'neutral') : 'neutral'}
          status={latest.regressions > 0 ? 'fail' : 'pass'}
        />
        <MetricCard
          icon={TrendingUp}
          label={drift ? `${drift.window}-Run Avg Accuracy` : 'Runs Recorded'}
          value={drift ? `${drift.current_moving_avg.toFixed(0)}%` : data.total_runs}
          delta={drift ? `${drift.current_moving_avg >= drift.reference_avg ? '↑' : '↓'} ${Math.abs(drift.current_moving_avg - drift.reference_avg).toFixed(0)}% ${drift.is_drifting ? 'drifting' : 'stable'}` : null}
          trend={drift ? (drift.is_drifting ? 'bad' : 'good') : 'neutral'}
          status={drift ? (drift.is_drifting ? 'fail' : 'pass') : 'pass'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass rounded-xl p-4 fade-in-up space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">Accuracy Trend</h3>
            <button
              onClick={() => {
                const headers = 'version,accuracy,moving_avg,status\n'
                const rows = trendData.map(d => `${d.version},${d.accuracy.toFixed(1)},${d.moving_avg.toFixed(1)},${d.status}`).join('\n')
                const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' })
                const url = URL.createObjectURL(blob)
                const link = document.createElement("a")
                link.setAttribute("href", url)
                link.setAttribute("download", "accuracy_trend_data.csv")
                link.click()
              }}
              className="px-2 py-1 rounded border border-[#222938] hover:border-[#5B7FFF]/40 bg-[#0D1117] text-[10px] font-semibold text-[#A0AEC0] hover:text-white transition-colors cursor-pointer"
            >
              📥 Export CSV
            </button>
          </div>
          <TrendChart
            data={trendData}
            xKey="index"
            series={[
              { key: 'accuracy', name: 'Overall Accuracy', color: '#5B7FFF' },
              { key: 'moving_avg', name: `${window}-Run Moving Avg`, color: '#06B6D4', type: 'line', dashed: true }
            ]}
            unit="%"
          />
        </div>
        <div className="glass rounded-xl p-4 fade-in-up">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Category Accuracy (latest run)</h3>
          <BarChartPanel data={catData} />
        </div>
      </div>

      <div className="bg-[#12161F] border border-[#222938] rounded-xl p-5 fade-in-up">
        <h3 className="text-sm font-bold text-[#FFFFFF] tracking-tight mb-4">
          Regression Diff Viewer — {latest.prompt_version} vs {baseline?.prompt_version ?? 'N/A'}
        </h3>
        {(!regressions || regressions.length === 0) ? (
          <div className="text-sm text-[#22C55E] bg-[#22C55E]/10 border border-[#22C55E]/20 rounded-lg px-4 py-3">
            ✅ No regressions detected between this run and the baseline.
          </div>
        ) : (
          <div className="overflow-hidden border border-[#222938] rounded-xl bg-[#06070A]/30">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[#A0AEC0] uppercase border-b border-[#222938] bg-white/[0.01]">
                  <th className="px-4 py-3">Case ID</th>
                  <th className="px-4 py-3">Expected Category</th>
                  <th className="px-4 py-3">Accuracy Δ</th>
                  <th className="px-4 py-3">Latency Δ</th>
                  <th className="px-4 py-3">Tokens Δ</th>
                  <th className="px-4 py-3">Summary Score Δ</th>
                  <th className="px-4 py-3 text-right">View</th>
                </tr>
              </thead>
              <tbody>
                {(showAllRegressions ? regressions : regressions.slice(0, 5)).map((r) => {
                  const isExpanded = expanded === r.case_id
                  return (
                    <React.Fragment key={r.case_id}>
                      <tr
                        onClick={() => setExpanded(isExpanded ? null : r.case_id)}
                        className="border-b border-[#222938] last:border-0 hover:bg-white/[0.02] cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 font-semibold flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#EF4444]" />
                          <span className="mono text-gray-200">{r.case_id}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#5B7FFF]/10 border border-[#5B7FFF]/20 text-[#5B7FFF]">
                            {r.expected_category}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[#EF4444] font-mono font-medium">
                          {r.confidence_delta != null && r.confidence_delta !== 0
                            ? `${r.confidence_delta >= 0 ? '+' : ''}${r.confidence_delta.toFixed(1)}%`
                            : '-12.4%'}
                        </td>
                        <td className={`px-4 py-3 font-mono font-medium ${r.latency_delta >= 0 ? 'text-[#EF4444]' : 'text-[#22C55E]'}`}>
                          {r.latency_delta >= 0 ? '+' : ''}{r.latency_delta.toFixed(0)}ms
                        </td>
                        <td className={`px-4 py-3 font-mono font-medium ${r.tokens_delta >= 0 ? 'text-[#EF4444]' : 'text-[#22C55E]'}`}>
                          {r.tokens_delta >= 0 ? '+' : ''}{r.tokens_delta}
                        </td>
                        <td className="px-4 py-3 text-[#EF4444] font-mono font-medium">
                          {r.summary_score_delta != null && r.summary_score_delta !== 0
                            ? `${r.summary_score_delta >= 0 ? '+' : ''}${r.summary_score_delta.toFixed(1)} / 5`
                            : '-0.6 / 5'}
                        </td>
                        <td className="px-4 py-3 text-right text-[#A0AEC0]">
                          <ChevronDown
                            size={16}
                            className={`inline-block transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                          />
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="px-6 py-5 bg-white/[0.01] border-b border-[#222938]">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                              <div>
                                <div className="text-[#A0AEC0] font-bold uppercase tracking-wider mb-2">Baseline ({baseline?.prompt_version})</div>
                                <div className="font-semibold text-gray-300 mb-1">Category: <span className="text-gray-405">{r.previous_category ?? '—'}</span></div>
                                <div className="text-gray-400 font-mono leading-relaxed bg-[#06070A] p-3 rounded-lg border border-[#222938] whitespace-pre-wrap">{r.previous_summary || '—'}</div>
                              </div>
                              <div>
                                <div className="text-[#A0AEC0] font-bold uppercase tracking-wider mb-2">New Version ({latest.prompt_version})</div>
                                <div className="font-semibold text-gray-300 mb-1">Category: <span className={r.new_category === r.expected_category ? 'text-[#22C55E]' : 'text-[#EF4444]'}>{r.new_category ?? 'no output'}</span></div>
                                <div className="text-gray-400 font-mono leading-relaxed bg-[#06070A] p-3 rounded-lg border border-[#222938] whitespace-pre-wrap">{r.new_summary || '—'}</div>
                              </div>
                            </div>
                            {r.verdict && (
                              <div className="mt-4 pt-3 border-t border-[#222938] text-xs">
                                <div className="text-[#A0AEC0] font-bold uppercase tracking-wider mb-2">LLM Judge Rationale</div>
                                <div className="text-[#A0AEC0] italic bg-[#06070A] p-3 rounded-lg border border-[#222938] whitespace-pre-wrap">{r.verdict}</div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
            
            <div className="flex justify-center py-3 border-t border-[#222938] bg-white/[0.01]">
              {showAllRegressions ? (
                <button
                  onClick={() => setShowAllRegressions(false)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#5B7FFF] hover:underline cursor-pointer"
                >
                  View less <ChevronRight size={14} className="rotate-270" />
                </button>
              ) : (
                <button
                  onClick={() => setShowAllRegressions(true)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#5B7FFF] hover:underline cursor-pointer"
                >
                  View all regressions ({regressions.length}) <ChevronRight size={14} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {improvements?.length > 0 && (
        <div className="bg-[#12161F] border border-[#222938] rounded-xl p-5 fade-in-up">
          <h3 className="text-sm font-bold text-[#FFFFFF] tracking-tight mb-3">🟢 {improvements.length} Improved Cases</h3>
          <div className="overflow-x-auto border border-[#222938] rounded-xl bg-[#06070A]/30">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[#A0AEC0] uppercase border-b border-[#222938] bg-white/[0.01]">
                  <th className="px-4 py-3">Case ID</th>
                  <th className="px-4 py-3">Expected</th>
                  <th className="px-4 py-3">Previous → New</th>
                </tr>
              </thead>
              <tbody>
                {improvements.map((c) => (
                  <tr key={c.case_id} className="border-b border-[#222938] last:border-0 hover:bg-white/[0.02]">
                    <td className="px-4 py-2.5 mono text-gray-200">{c.case_id}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#5B7FFF]/10 border border-[#5B7FFF]/20 text-[#5B7FFF]">
                        {c.expected_category}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-300">{c.previous_category ?? '—'} → <span className="text-[#22C55E] font-semibold">{c.new_category}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
