import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Search, Target, AlertTriangle, TrendingUp, Clock, Coins, Brain, FileText, ChevronRight } from 'lucide-react'
import { api } from '../api'
import Badge, { statusVariant } from '../components/Badge'
import MetricCard from '../components/MetricCard'
import BarChartPanel from '../components/BarChartPanel'
import { RowSkeleton } from '../components/Skeleton'

function highlight(text, query) {
  if (!query) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

function getDevOpsDetails(runId) {
  const hash = runId.replace(/[^a-zA-Z0-9]/g, '').slice(-7) || 'f0a1e3b'
  let branch = 'main'
  if (runId.includes('v8')) branch = 'feature/classifier-v8'
  else if (runId.includes('v9')) branch = 'fix/summary-relevance'
  else if (runId.includes('v1')) branch = 'feature/evals-v1'

  const prNum = parseInt(hash, 16) % 100 + 42

  return {
    commit: hash,
    branch: branch,
    pr: `#${prNum}`,
  }
}

function getProviderBadge(provider) {
  const p = provider ? provider.toLowerCase() : ''
  if (p === 'openai') {
    return (
      <span className="inline-flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2.5 py-0.5 rounded-md">
        <span className="w-1 h-1 rounded-full bg-emerald-400" /> OpenAI
      </span>
    )
  }
  if (p === 'anthropic') {
    return (
      <span className="inline-flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[10px] font-bold px-2.5 py-0.5 rounded-md">
        <span className="w-1 h-1 rounded-full bg-amber-400" /> Anthropic
      </span>
    )
  }
  if (p === 'gemini') {
    return (
      <span className="inline-flex items-center gap-1.5 bg-violet-500/10 border border-violet-500/20 text-violet-400 text-[10px] font-bold px-2.5 py-0.5 rounded-md">
        <span className="w-1 h-1 rounded-full bg-violet-400" /> Gemini
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 bg-white/5 border border-white/10 text-gray-400 text-[10px] font-bold px-2.5 py-0.5 rounded-md">
      <span className="w-1 h-1 rounded-full bg-gray-400" /> {provider || 'Mock'}
    </span>
  )
}

export default function Runs() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [selected, setSelected] = useState(null)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    api.runs()
      .then((rs) => {
        setRuns(rs)
        const wanted = searchParams.get('open')
        const initial = wanted ? rs.find((r) => r.run_id === wanted) : rs[0]
        setSelected(initial ?? rs[0] ?? null)
      })
      .catch((e) => toast.error(`Failed to load runs: ${e.message}`))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!query) return runs
    const q = query.toLowerCase()
    return runs.filter((r) => r.run_id.toLowerCase().includes(q) || r.prompt_version.toLowerCase().includes(q))
  }, [runs, query])

  const visibleRuns = useMemo(() => {
    return showAll ? filtered : filtered.slice(0, 10)
  }, [filtered, showAll])

  if (loading) return <RowSkeleton rows={8} />

  return (
    <div className="space-y-6">
      <div className="glass rounded-xl overflow-hidden border border-[#222938]">
        <div className="flex items-center gap-2 px-4 py-3.5 border-b border-[#222938] bg-white/[0.01]">
          <Search size={15} className="text-gray-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search runs by version, branch or run ID…"
            className="bg-transparent outline-none flex-1 text-sm placeholder:text-gray-500 text-gray-100"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase bg-white/[0.02] border-b border-[#222938]">
                <th className="px-4 py-3">Run ID & DevOps Info</th>
                <th className="px-4 py-3">Version & Model</th>
                <th className="px-4 py-3">LLM Provider</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Accuracy</th>
                <th className="px-4 py-3">Regressions</th>
                <th className="px-4 py-3">p-value</th>
              </tr>
            </thead>
            <tbody>
              {visibleRuns.map((r) => {
                const devops = getDevOpsDetails(r.run_id)
                return (
                  <tr
                    key={r.run_id}
                    onClick={() => {
                      setSelected(r)
                      setSearchParams({})
                    }}
                    className={`border-t border-[#222938] cursor-pointer transition-colors hover:bg-white/5 ${selected?.run_id === r.run_id ? 'bg-[#5B7FFF]/10' : ''
                      }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="mono text-gray-200 text-sm font-semibold">{highlight(r.run_id, query)}</span>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500 font-mono">
                          <span className="bg-white/5 border border-[#222938] px-1.5 py-0.5 rounded text-gray-400 font-medium">{devops.branch}</span>
                          <span>·</span>
                          <span className="text-indigo-400 font-semibold">{devops.commit}</span>
                          <span>·</span>
                          <span className="text-gray-405 font-semibold">{devops.pr}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-0.5">
                        <Badge variant="version">{highlight(r.prompt_version, query)}</Badge>
                        <span className="text-[10px] text-gray-500 font-mono tracking-tight mt-0.5">{r.model}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">{getProviderBadge(r.provider)}</td>
                    <td className="px-4 py-3"><Badge variant={statusVariant(r.status)} showIcon>{r.status}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5 w-28">
                        <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-400 transition-all duration-500"
                            style={{ width: `${r.overall_accuracy}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400 w-9 font-semibold">{r.overall_accuracy.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-300 font-semibold">{r.regressions}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono">{r.p_value != null ? r.p_value.toFixed(3) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {filtered.length > 10 && (
            <div className="flex justify-center py-3 border-t border-[#222938] bg-white/[0.01]">
              {showAll ? (
                <button
                  onClick={() => setShowAll(false)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#5B7FFF] hover:underline cursor-pointer"
                >
                  Show less <ChevronRight size={14} className="rotate-270" />
                </button>
              ) : (
                <button
                  onClick={() => setShowAll(true)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#5B7FFF] hover:underline cursor-pointer"
                >
                  Show all {filtered.length} runs <ChevronRight size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {selected && <RunDetail run={selected} />}
    </div>
  )
}

function RunDetail({ run }) {
  const catData = Object.entries(run.category_accuracy).map(([name, value]) => ({ name, value }))
  const devops = getDevOpsDetails(run.run_id)

  return (
    <div className="glass rounded-xl p-5 border border-[#222938] fade-in-up space-y-5">
      <div className="flex items-center gap-2 border-b border-[#222938] pb-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <Badge variant="version">{run.prompt_version}</Badge>
            <Badge variant={statusVariant(run.status)} showIcon>{run.status}</Badge>
          </div>
          <span className="text-[11px] text-gray-500 mono mt-1.5">{run.run_id}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={() => window.open(`${import.meta.env.VITE_API_URL || '/api'}/reports/${run.run_id}`, '_blank')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#222938] bg-[#0D1117] text-xs font-semibold text-[#A0AEC0] hover:text-white hover:border-[#5B7FFF]/40 transition-colors"
          >
            <FileText size={13} /> View HTML Report
          </button>
          {getProviderBadge(run.provider)}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-white/[0.01] border border-[#222938] rounded-xl p-4 text-xs text-gray-400">
        <div>
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[9px] block mb-1">Branch</span>
          <span className="font-mono text-gray-300 font-semibold">{devops.branch}</span>
        </div>
        <div>
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[9px] block mb-1">Commit Hash</span>
          <span className="font-mono text-indigo-400 hover:underline cursor-pointer">{devops.commit}</span>
        </div>
        <div>
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[9px] block mb-1">GitHub PR</span>
          <span className="text-indigo-400 hover:underline font-semibold cursor-pointer">{devops.pr}</span>
        </div>
        <div>
          <span className="text-gray-500 font-bold uppercase tracking-wider text-[9px] block mb-1">Model under test</span>
          <span className="font-semibold text-gray-300">{run.model}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard icon={Target} label="Accuracy" value={`${run.overall_accuracy.toFixed(1)}%`} status={run.status} />
        <MetricCard icon={AlertTriangle} label="Regressions" value={run.regressions} status={run.regressions > 0 ? 'fail' : 'pass'} />
        <MetricCard icon={TrendingUp} label="Improvements" value={run.improvements} status={run.improvements > 0 ? 'pass' : 'neutral'} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <MetricCard icon={Clock} label="Avg Latency" value={`${run.avg_latency_ms.toFixed(0)} ms`} />
        <MetricCard icon={Coins} label="Avg Tokens" value={run.avg_tokens.toFixed(0)} />
        <MetricCard icon={Brain} label="Summary Judge" value={`${run.avg_summary_relevance.toFixed(1)}/5`} />
      </div>

      <div className="text-xs text-gray-400 space-y-2 bg-white/[0.01] border border-[#222938] rounded-xl p-4">
        <div className="flex justify-between"><span className="text-gray-500">Run Timestamp</span> <span className="font-medium text-gray-300 font-mono">{run.timestamp}</span></div>
        {run.p_value != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">Statistical Significance</span>{' '}
            <span className="font-semibold text-gray-300">
              {run.statistically_significant ? '✅ Yes (Significant)' : '❌ No'} (p = {run.p_value.toFixed(3)})
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="border border-[#222938] bg-[#0D1117]/30 rounded-xl p-4 space-y-3">
          <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Category Accuracy Breakdown</h4>
          <BarChartPanel data={catData} height={200} />
        </div>
        <div className="border border-[#222938] bg-[#0D1117]/30 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Accuracy by Difficulty</h4>
            <p className="text-[10px] text-gray-500 mt-0.5">Test suite performance categorized by complexity level</p>
          </div>
          <div className="flex items-center justify-around py-3">
            {['easy', 'medium', 'hard'].map((level) => {
              const stats = run.difficulty_breakdown?.[level] || { passed: 0, total: 0 }
              const pct = stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0
              const color = level === 'easy' ? '#22C55E' : level === 'medium' ? '#5B7FFF' : '#EF4444'
              const radius = 26
              const circumference = 2 * Math.PI * radius
              const strokeDashoffset = circumference - (pct / 100) * circumference

              return (
                <div key={level} className="flex flex-col items-center gap-1.5">
                  <div className="relative w-16 h-16 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="32" cy="32" r={radius} stroke="#222938" strokeWidth="4.5" fill="transparent" />
                      <circle
                        cx="32"
                        cy="32"
                        r={radius}
                        stroke={color}
                        strokeWidth="4.5"
                        fill="transparent"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                        style={{ filter: `drop-shadow(0 0 3px ${color}30)` }}
                      />
                    </svg>
                    <span className="absolute text-[10px] font-extrabold text-white">{pct}%</span>
                  </div>
                  <span className="text-[9px] font-bold uppercase tracking-wider text-gray-400 capitalize">{level}</span>
                  <span className="text-[9px] text-gray-500 font-mono">{stats.passed}/{stats.total} passed</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}