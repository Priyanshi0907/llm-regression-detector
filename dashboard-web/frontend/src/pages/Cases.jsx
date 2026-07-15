import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Search, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../api'
import Badge from '../components/Badge'
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

export default function Cases() {
  const [runs, setRuns] = useState([])
  const [runId, setRunId] = useState(null)
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [onlyFailures, setOnlyFailures] = useState(false)
  const [catFilter, setCatFilter] = useState('')
  const [selected, setSelected] = useState(null)
  const [promptText, setPromptText] = useState('')

  useEffect(() => {
    api.runs().then((rs) => {
      setRuns(rs)
      if (rs[0]) setRunId(rs[0].run_id)
    }).catch((e) => toast.error(`Failed to load runs: ${e.message}`))
  }, [])

  useEffect(() => {
    if (!runId) return
    setLoading(true)
    api.runCases(runId)
      .then((cs) => {
        setCases(cs)
        setSelected(cs[0] ?? null)
      })
      .catch((e) => toast.error(`Failed to load cases: ${e.message}`))
      .finally(() => setLoading(false))

    const currentRun = runs.find(r => r.run_id === runId)
    if (currentRun) {
      fetch(`/api/prompts/${encodeURIComponent(currentRun.prompt_version)}`)
        .then(res => res.json())
        .then(data => setPromptText(data.content || ''))
        .catch(() => setPromptText(''))
    } else {
      setPromptText('')
    }
  }, [runId, runs])

  const categories = useMemo(() => [...new Set(cases.map((c) => c.expected_category))].sort(), [cases])

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      if (onlyFailures && c.passed) return false
      if (catFilter && c.expected_category !== catFilter) return false
      if (query) {
        const q = query.toLowerCase()
        if (!c.case_id.toLowerCase().includes(q) && !c.input.toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [cases, query, onlyFailures, catFilter])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={runId ?? ''}
          onChange={(e) => setRunId(e.target.value)}
          className="glass rounded-lg px-3 py-2 text-sm outline-none"
        >
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id} className="bg-[#12141c]">
              {r.run_id} · {r.prompt_version}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-400">
          <input type="checkbox" checked={onlyFailures} onChange={(e) => setOnlyFailures(e.target.checked)} />
          Only failures
        </label>
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="glass rounded-lg px-3 py-2 text-sm outline-none"
        >
          <option value="" className="bg-[#12141c]">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c} className="bg-[#12141c]">{c}</option>
          ))}
        </select>
        <div className="flex items-center gap-2 glass rounded-lg px-3 py-2 flex-1 min-w-[200px]">
          <Search size={14} className="text-gray-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by ID or email content…"
            className="bg-transparent outline-none flex-1 text-sm placeholder:text-gray-500"
          />
        </div>
      </div>

      {loading ? (
        <RowSkeleton rows={8} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-2 glass rounded-xl overflow-hidden max-h-[70vh] overflow-y-auto">
            {filtered.length === 0 && <div className="p-6 text-center text-sm text-gray-500">No cases match filters.</div>}
            {filtered.map((c) => (
              <button
                key={c.case_id}
                onClick={() => setSelected(c)}
                className={`w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors flex items-start gap-2 ${
                  selected?.case_id === c.case_id ? 'bg-indigo-500/10' : ''
                }`}
              >
                {c.passed ? (
                  <CheckCircle2 size={15} className="text-emerald-400 mt-0.5 shrink-0" />
                ) : (
                  <XCircle size={15} className="text-red-400 mt-0.5 shrink-0" />
                )}
                <div className="min-w-0">
                  <div className="text-xs mono text-gray-500">{highlight(c.case_id, query)}</div>
                  <div className="text-sm text-gray-300 truncate">{highlight(c.input, query)}</div>
                </div>
              </button>
            ))}
          </div>

          <div className="lg:col-span-3">
            {selected && <CaseDetail c={selected} promptText={promptText} />}
          </div>
        </div>
      )}
    </div>
  )
}

function getSummaryDiff(expected, actual) {
  if (!expected || !actual) return { expectedHtml: expected || '', actualHtml: actual || '' }
  const expWords = expected.split(/\s+/)
  const actWords = actual.split(/\s+/)
  
  const expectedHtml = expWords.map(w => {
    const clean = w.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").toLowerCase()
    const matches = actWords.some(aw => aw.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").toLowerCase() === clean)
    return matches ? w : `<span class="bg-[#EF4444]/25 text-[#EF4444] border border-[#EF4444]/30 px-1 py-0.5 rounded font-semibold">${w}</span>`
  }).join(' ')

  const actualHtml = actWords.map(w => {
    const clean = w.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").toLowerCase()
    const matches = expWords.some(ew => ew.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").toLowerCase() === clean)
    return matches ? w : `<span class="bg-[#22C55E]/25 text-[#22C55E] border border-[#22C55E]/30 px-1 py-0.5 rounded font-semibold">${w}</span>`
  }).join(' ')

  return { expectedHtml, actualHtml }
}

function CaseDetail({ c, promptText }) {
  const { expectedHtml, actualHtml } = getSummaryDiff(c.expected_summary, c.actual_summary)
  
  // Calculate mock breakdowns
  const queueTime = 45
  const genTime = Math.max(10, Math.round(c.latency_ms - queueTime))
  const queuePct = Math.round((queueTime / c.latency_ms) * 100)
  const genPct = 100 - queuePct

  const promptTokens = Math.max(10, Math.round(c.tokens_used * 0.85))
  const compTokens = Math.max(1, c.tokens_used - promptTokens)
  const promptPct = Math.round((promptTokens / c.tokens_used) * 100)
  const compPct = 100 - promptPct

  return (
    <div className="space-y-4 fade-in-up">
      <div className="flex items-center gap-2">
        <span className="mono text-sm text-gray-500">{c.case_id}</span>
        <Badge variant={c.passed ? 'pass' : 'fail'} showIcon>{c.passed ? 'PASS' : 'FAIL'}</Badge>
      </div>

      <div className="glass rounded-xl p-4">
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">📧 Input Email</h4>
        <div className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm mono text-gray-200 leading-relaxed">
          {c.input}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="glass rounded-xl p-4 border border-[#222938]">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">🎯 Expected Output</h4>
          <Badge variant="version">{c.expected_category}</Badge>
          <div className="text-[10px] font-bold text-gray-550 uppercase tracking-wider mt-4 mb-1">Expected Summary</div>
          <div className="text-sm text-gray-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: expectedHtml }} />
        </div>
        <div className="glass rounded-xl p-4 border border-[#222938]">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2 flex items-center gap-1.5">
            🤖 Predicted Output {c.category_match ? <CheckCircle2 size={13} className="text-emerald-400" /> : <XCircle size={13} className="text-red-400" />}
          </h4>
          <Badge variant={c.category_match ? 'pass' : 'fail'}>{c.actual_category ?? 'no output'}</Badge>
          <div className="text-[10px] font-bold text-gray-555 uppercase tracking-wider mt-4 mb-1">Predicted Summary · {c.confidence?.toFixed(0)}% confidence</div>
          <div className="text-sm text-gray-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: actualHtml }} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Token breakdown progress chart */}
        <div className="glass rounded-xl p-4 border border-[#222938]">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">Token Usage Breakdown</h4>
          <div className="flex h-2 rounded-full overflow-hidden bg-white/5 mb-3">
            <div className="h-full bg-[#F59E0B]" style={{ width: `${promptPct}%` }} title={`Prompt: ${promptTokens} tokens`} />
            <div className="h-full bg-[#22C55E]" style={{ width: `${compPct}%` }} title={`Completion: ${compTokens} tokens`} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 font-mono">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-[#F59E0B]" /> Input: {promptTokens} ({promptPct}%)</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-[#22C55E]" /> Output: {compTokens} ({compPct}%)</span>
          </div>
        </div>

        {/* Execution timeline chart */}
        <div className="glass rounded-xl p-4 border border-[#222938]">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">Execution Timeline</h4>
          <div className="flex h-2 rounded-full overflow-hidden bg-white/5 mb-3">
            <div className="h-full bg-white/10" style={{ width: `${queuePct}%` }} title={`Queue: ${queueTime}ms`} />
            <div className="h-full bg-[#5B7FFF]" style={{ width: `${genPct}%` }} title={`Generation: ${genTime}ms`} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 font-mono">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-white/15" /> Queue: {queueTime}ms ({queuePct}%)</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-[#5B7FFF]" /> LLM Call: {genTime}ms ({genPct}%)</span>
          </div>
        </div>
      </div>

      {c.judge_rationale && (
        <div className="glass rounded-xl p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">⚖️ LLM Judge Rationale</h4>
          <p className="text-xs text-gray-300 leading-relaxed bg-[#0D1117]/30 p-3 rounded-lg border border-[#222938]">{c.judge_rationale}</p>
        </div>
      )}

      {promptText && (
        <div className="glass rounded-xl p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">📄 Prompt Template Under Test</h4>
          <pre className="bg-[#0D1117] border border-[#222938] rounded-lg p-3 text-xs text-gray-400 font-mono overflow-x-auto whitespace-pre leading-relaxed max-h-56">
            {promptText}
          </pre>
        </div>
      )}

      <div className={`glass rounded-xl p-4 border ${c.passed ? 'border-[#22C55E]/15' : 'border-[#EF4444]/15'}`}>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">🔍 Reason for Failure / Verdict</h4>
        <p className={`text-xs ${c.passed ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>{c.failure_explanation}</p>
      </div>
    </div>
  )
}
