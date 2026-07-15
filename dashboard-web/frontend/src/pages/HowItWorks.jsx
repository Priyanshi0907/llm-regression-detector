import { useEffect, useState } from 'react'
import { GitBranch, PlayCircle, Scale, GitCompareArrows, Activity, MonitorSmartphone, MessageSquare, ShieldOff } from 'lucide-react'
import { api } from '../api'
import Badge from '../components/Badge'

const PIPELINE = [
  { icon: GitBranch, title: 'Prompt changed', desc: 'A PR modifies /prompts, /golden_dataset, or /src' },
  { icon: PlayCircle, title: 'GitHub Actions triggers', desc: 'llm-eval.yml runs automatically on the PR' },
  { icon: Scale, title: 'Eval pipeline runs', desc: 'Every case run through the LLM feature — optionally across multiple providers side-by-side' },
  { icon: GitCompareArrows, title: 'Scored & diffed', desc: 'Category match + rubric-driven LLM-as-judge + optional semantic similarity, vs. baseline' },
  { icon: Activity, title: 'Drift checked', desc: 'A 7-run rolling average catches gradual degradation no single run would trip' },
  { icon: MonitorSmartphone, title: 'Report + DB committed', desc: 'HTML report generated; results DB committed back to the repo on merge' },
  { icon: MessageSquare, title: 'Slack / Discord / Email alerted', desc: 'On WARNING/FAIL, a structured alert fires on every channel you\'ve configured' },
  { icon: ShieldOff, title: 'Merge blocked on FAIL', desc: 'A statistically significant regression exits non-zero, failing the CI check' },
]

const METHOD = [
  {
    title: 'Category classification',
    detail: 'Deterministic exact-match against the golden dataset label. Binary — either right or wrong, no fuzziness.',
  },
  {
    title: 'Summary relevance — configurable-rubric LLM-as-judge',
    detail: 'A second LLM call scores the generated summary 1–5 against a YAML-defined rubric (golden_dataset/judge_rubric.yaml) — edit criteria and weights there without touching code.',
  },
  {
    title: 'Semantic similarity (optional second dimension)',
    detail: 'Embeddings cosine similarity between expected and actual summaries, toggled via SEMANTIC_SIMILARITY_ENABLED. When off (or no OpenAI key), falls back to a labeled token-overlap approximation rather than silently omitting the field.',
  },
  {
    title: 'Multi-provider support',
    detail: 'The feature under test can run against OpenAI, Anthropic, or Gemini — same prompt, same dataset, one run per provider — so you can see how the same prompt performs across models before committing to one.',
  },
  {
    title: 'Confidence',
    detail: "Self-reported by the model as part of its own structured JSON output. Not calibrated — treat it as the model's own claim, not a guaranteed probability.",
  },
  {
    title: 'Regression significance',
    detail: 'A two-proportion z-test (α = 0.05) on pass rates between the current run and its baseline, so a couple of flipped cases in a 60-case dataset doesn\'t trigger a false alarm.',
  },
  {
    title: 'Drift detection',
    detail: 'A rolling N-run moving average of accuracy, compared to the first full window ever recorded — catches slow degradation across many small changes that no single-run diff would flag.',
  },
]

const NOT_USED = ['BERTScore', 'ROUGE', 'Promptfoo', 'DeepEval', 'LangSmith']

export default function HowItWorks() {
  const [meta, setMeta] = useState(null)
  useEffect(() => { api.meta().then(setMeta).catch(() => {}) }, [])

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-bold text-gray-100 mb-1">The automation pipeline</h2>
        <p className="text-sm text-gray-500 mb-5">
          Every prompt change goes through this end-to-end, not just a manual dashboard check.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {PIPELINE.map((step, i) => (
            <div key={step.title} className="glass glass-hover rounded-xl p-4 relative fade-in-up" style={{ animationDelay: `${i * 40}ms` }}>
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center mb-3">
                <step.icon size={16} className="text-indigo-300" />
              </div>
              <div className="text-xs font-bold text-gray-500 mb-1">STEP {i + 1}</div>
              <div className="text-sm font-semibold text-gray-100 mb-1">{step.title}</div>
              <div className="text-xs text-gray-500 leading-relaxed">{step.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-lg font-bold text-gray-100 mb-1">Evaluation methodology</h2>
        <p className="text-sm text-gray-500 mb-5">What actually computes each number you see on this dashboard.</p>
        <div className="space-y-3">
          {METHOD.map((m) => (
            <div key={m.title} className="glass rounded-xl p-4">
              <div className="text-sm font-semibold text-gray-100 mb-1">{m.title}</div>
              <div className="text-xs text-gray-500 leading-relaxed">{m.detail}</div>
            </div>
          ))}
        </div>
      </div>

      {meta?.rubric && (
        <div>
          <h2 className="text-lg font-bold text-gray-100 mb-1">Current judge rubric</h2>
          <p className="text-sm text-gray-500 mb-4">
            Live from <code className="text-gray-400">golden_dataset/judge_rubric.yaml</code> — edit that file to change what "good" means.
          </p>
          <div className="glass rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase bg-white/[0.02]">
                  <th className="px-4 py-2.5">Criterion</th>
                  <th className="px-4 py-2.5">Weight</th>
                  <th className="px-4 py-2.5">Description</th>
                </tr>
              </thead>
              <tbody>
                {meta.rubric.criteria?.map((c) => (
                  <tr key={c.name} className="border-t border-white/5">
                    <td className="px-4 py-2.5 font-semibold text-gray-200">{c.name}</td>
                    <td className="px-4 py-2.5 text-gray-400">{c.weight}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{c.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {meta && (
        <div>
          <h2 className="text-lg font-bold text-gray-100 mb-1">Provider availability</h2>
          <div className="flex gap-3">
            {meta.supported_providers?.map((p) => (
              <div key={p} className="glass rounded-xl p-3 flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${meta.provider_availability[p] ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="text-sm capitalize text-gray-200">{p}</span>
                <Badge variant={meta.provider_availability[p] ? 'pass' : 'warning'}>
                  {meta.provider_availability[p] ? 'live key configured' : 'mock fallback'}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="glass rounded-xl p-4 border border-amber-500/20">
        <div className="text-sm font-semibold text-amber-300 mb-2">Not currently used (roadmap, not claimed)</div>
        <div className="flex flex-wrap gap-2">
          {NOT_USED.map((n) => (
            <span key={n} className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-gray-400 border border-white/10">
              {n}
            </span>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-3">
          No dependency on third-party eval frameworks — this is a from-scratch harness.
          BERTScore/ROUGE would only add value over embeddings-based semantic similarity in
          narrow cases; not worth the extra dependency weight at this dataset size.
        </p>
      </div>

      {meta && (
        <div className="glass rounded-xl p-4">
          <div className="text-sm font-semibold text-gray-100 mb-3">Current configuration</div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <ConfigRow label="Mode" value={meta.mock_mode ? 'Demo (mock)' : 'Live'} />
            <ConfigRow label="Feature provider / model" value={`${meta.llm_provider} / ${meta.llm_model}`} />
            <ConfigRow label="Judge provider / model" value={`${meta.judge_provider} / ${meta.judge_model}`} />
            <ConfigRow label="Semantic similarity" value={meta.semantic_similarity_enabled ? 'Enabled (real embeddings)' : 'Off (token-overlap fallback)'} />
            <ConfigRow label="Warning threshold" value={`${meta.warning_threshold_pct} pp`} />
            <ConfigRow label="Critical threshold" value={`${meta.critical_threshold_pct} pp`} />
            <ConfigRow label="Drift window" value={`${meta.drift_window} runs`} />
            <ConfigRow label="Alert channels" value={[meta.slack_configured && 'Slack', meta.discord_configured && 'Discord', meta.email_configured && 'Email'].filter(Boolean).join(', ') || 'None configured'} />
          </div>
        </div>
      )}
    </div>
  )
}

function ConfigRow({ label, value }) {
  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2">
      <div className="text-gray-500">{label}</div>
      <div className="text-gray-200 font-semibold mt-0.5">{value}</div>
    </div>
  )
}
