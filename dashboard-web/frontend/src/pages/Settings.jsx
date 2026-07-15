import { useEffect, useState, useRef } from 'react'
import toast from 'react-hot-toast'
import { Play, HelpCircle, Loader2, Copy, Check, ShieldCheck, Database, Key, Brain } from 'lucide-react'
import { api } from '../api'

export default function Settings() {
  const [meta, setMeta] = useState(null)
  const [prompts, setPrompts] = useState([])
  const [evalStrategy, setEvalStrategy] = useState('llm_judge')
  const [selectedPrompt, setSelectedPrompt] = useState('')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [activeTab, setActiveTab] = useState('controls')
  const [output, setOutput] = useState(null)
  const [copied, setCopied] = useState(false)
  const terminalEndRef = useRef(null)

  useEffect(() => {
    Promise.all([api.meta(), api.prompts()])
      .then(([m, p]) => {
        setMeta(m)
        setPrompts(p)
        if (p.length > 0) {
          setSelectedPrompt(p[0])
        }
      })
      .catch((e) => toast.error(`Failed to load settings: ${e.message}`))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (output) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [output])

  async function handleRunEval() {
    if (!selectedPrompt) {
      toast.error('Please select a prompt file')
      return
    }
    setRunning(true)
    setOutput({ stdout: '🚀 Spawning pipeline process...\n$ python -m src.cli --prompt ' + selectedPrompt + ' --no-slack\n\n', stderr: '', returncode: null })
    
    try {
      const res = await api.runEval({ prompt_file: selectedPrompt })
      setOutput(res)
      if (res.returncode === 0) {
        toast.success('Evaluation PASSED successfully!')
      } else {
        toast.error('Evaluation finished with Warning/Regression status')
      }
    } catch (e) {
      toast.error(`Evaluation execution failed: ${e.message}`)
      setOutput({ stdout: '', stderr: 'SYSTEM_ERROR: ' + e.message, returncode: -1 })
    } finally {
      setRunning(false)
    }
  }

  function handleCopy() {
    if (!output) return
    const txt = `${output.stdout || ''}\n${output.stderr || ''}`
    navigator.clipboard.writeText(txt)
    setCopied(true)
    toast.success('Logs copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <Loader2 className="animate-spin text-indigo-400" size={32} />
      </div>
    )
  }

  const isMock = meta?.mock_mode

  return (
    <div className="space-y-6 max-w-4xl fade-in-up">
      {/* Top Banner Alert */}
      {isMock && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl px-4 py-3.5 text-sm flex items-start gap-2.5 shadow-lg shadow-amber-500/5">
          <span className="text-lg">🟡</span>
          <div>
            <strong>Running in Demo Mode</strong> — configuration controls below are read-only. Set <code className="text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded font-mono text-xs">MOCK_MODE=false</code> and input a real <code className="text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded font-mono text-xs">OPENAI_API_KEY</code> in <code className="text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded font-mono text-xs">.env</code> to edit these live.
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10 pb-px">
        <button
          onClick={() => setActiveTab('controls')}
          className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors -mb-px ${
            activeTab === 'controls'
              ? 'border-indigo-500 text-indigo-300 font-semibold'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          General Settings
        </button>
        <button
          onClick={() => setActiveTab('raw')}
          className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors -mb-px ${
            activeTab === 'raw'
              ? 'border-indigo-500 text-indigo-300 font-semibold'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          Raw JSON Config
        </button>
      </div>

      {activeTab === 'controls' && (
        <div className="space-y-6">
          
          {/* Card 1: Provider Availability */}
          <div className="glass rounded-xl overflow-hidden border border-white/10">
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5">
                <Key size={14} className="text-indigo-400" />
                LLM Provider Keys & Availability
              </h3>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Availability of configured API keys for evaluations. Inactive providers fall back to mock classification automatically.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {Object.entries(meta?.provider_availability || {}).map(([prov, active]) => (
                  <div key={prov} className="bg-white/[0.01] border border-white/5 rounded-lg p-3 flex items-center justify-between">
                    <span className="text-xs font-semibold capitalize text-gray-300">{prov}</span>
                    <span className={`inline-flex items-center gap-1 text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                      active 
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                        : 'bg-white/5 border-white/10 text-gray-500'
                    }`}>
                      {active ? 'active key' : 'inactive'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white/[0.01] px-5 py-3 border-t border-white/5 text-[10px] text-gray-500 flex items-center justify-between">
              <span>Keys are managed securely via environment settings.</span>
              <span className="font-mono text-gray-600">.env</span>
            </div>
          </div>

          {/* Card 2: Model Configuration */}
          <div className="glass rounded-xl overflow-hidden border border-white/10">
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5">
                <Brain size={14} className="text-indigo-400" />
                Evaluation Model Configurations
              </h3>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Select the target classifier model and the judge model used to score text summaries.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Classifier Model (Under Test)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="The primary LLM feature being evaluated.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <select disabled className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed appearance-none">
                    <option>{meta?.llm_model || 'gpt-4o-mini'}</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Judge Model (LLM-as-Judge)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="Model evaluating summary accuracy and grading notes.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <select disabled className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed appearance-none">
                    <option>{meta?.judge_model || 'gpt-4o-mini'}</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="bg-white/[0.01] px-5 py-3 border-t border-white/5 text-[10px] text-gray-500">
              Active Provider Config: <span className="font-semibold text-gray-400 capitalize">{meta?.llm_provider || 'openai'}</span>
            </div>
          </div>

          {/* Card 3: Evaluation Strategy */}
          <div className="glass rounded-xl overflow-hidden border border-white/10">
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-indigo-400" />
                Evaluation Strategy
              </h3>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Choose how LLM outputs are scored against golden dataset labels. Different strategies suit different output shapes.
              </p>

              <div className="space-y-2.5">
                {[
                  { id: 'exact_match', label: 'Exact Match', desc: 'Binary pass/fail — predicted output must exactly match the expected label. Best for deterministic, structured outputs.', badge: 'Deterministic' },
                  { id: 'semantic_similarity', label: 'Semantic Similarity', desc: 'Embeddings cosine similarity between predicted and expected text. Catches paraphrases that exact match would miss.', badge: 'Embeddings' },
                  { id: 'llm_judge', label: 'LLM-as-a-Judge', desc: 'A second LLM scores output quality against a configurable rubric (1–5 scale). Handles free-text where wording differs but meaning is correct.', badge: 'Recommended' },
                  { id: 'regex_match', label: 'Regex Match', desc: 'Validates output against regex patterns. Useful for structured formats like dates, IDs, or specific keyword presence.', badge: 'Pattern' },
                  { id: 'json_structure', label: 'JSON Structure Match', desc: 'Validates that output JSON conforms to an expected schema (keys, types, nesting). Ideal for tool-calling and function outputs.', badge: 'Schema' },
                ].map((strategy) => {
                  const isActive = evalStrategy === strategy.id
                  return (
                    <label
                      key={strategy.id}
                      className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isActive
                          ? 'bg-indigo-500/10 border-indigo-500/30 shadow-lg shadow-indigo-500/5'
                          : 'bg-white/[0.01] border-white/5 hover:border-white/15'
                      }`}
                    >
                      <input
                        type="radio"
                        name="evalStrategy"
                        value={strategy.id}
                        checked={isActive}
                        onChange={(e) => setEvalStrategy(e.target.value)}
                        className="mt-0.5 accent-indigo-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-semibold ${isActive ? 'text-indigo-300' : 'text-gray-300'}`}>{strategy.label}</span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${
                            strategy.badge === 'Recommended'
                              ? 'bg-indigo-500/15 border-indigo-500/25 text-indigo-400'
                              : 'bg-white/5 border-white/10 text-gray-500'
                          }`}>{strategy.badge}</span>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-1 leading-relaxed">{strategy.desc}</p>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>
            <div className="bg-white/[0.01] px-5 py-3 border-t border-white/5 text-[10px] text-gray-500 flex items-center justify-between">
              <span>Active strategy: <span className="font-semibold text-gray-400 capitalize">{evalStrategy.replace('_', ' ').replace('llm judge', 'LLM-as-a-Judge')}</span></span>
              <span className="font-mono text-gray-600">config.evaluation_method</span>
            </div>
          </div>

          {/* Card 4: Thresholds */}
          <div className="glass rounded-xl overflow-hidden border border-white/10">
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-indigo-400" />
                Regression Limits & CI Thresholds
              </h3>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Define regression percentage boundaries. Exceeding critical thresholds triggers non-zero exits to block CI merges.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Warning Threshold (%)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="Drop in accuracy triggering a soft Warning status.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <input
                    type="text"
                    disabled
                    value={meta?.warning_threshold_pct != null ? `${meta.warning_threshold_pct.toFixed(2)}%` : '3.00%'}
                    className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed font-mono"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Critical Threshold (%)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="Drop in accuracy triggering a fail merge block.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <input
                    type="text"
                    disabled
                    value={meta?.critical_threshold_pct != null ? `${meta.critical_threshold_pct.toFixed(2)}%` : '8.00%'}
                    className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="bg-white/[0.01] px-5 py-3 border-t border-white/5 text-[10px] text-gray-500">
              Regression calculations utilize two-proportion z-tests for statistical relevance.
            </div>
          </div>

          {/* Card 4: Drift Monitor */}
          <div className="glass rounded-xl overflow-hidden border border-white/10">
            <div className="p-5">
              <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5">
                <Database size={14} className="text-indigo-400" />
                Slow Drift Window Metrics
              </h3>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Tune rolling moving averages to catch slow accuracy declines over consecutive commits.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Drift Window (eval runs)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="Range used to calculate rolling moving averages.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <input
                    type="text"
                    disabled
                    value={meta?.drift_window != null ? `${meta.drift_window} runs` : '7 runs'}
                    className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed font-mono"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-gray-400 mb-1.5 flex items-center gap-1.5 uppercase tracking-wider">
                    Drift Threshold (%)
                    <span className="text-gray-500 hover:text-gray-400 cursor-help" title="Decline in moving average triggering slow drift alerts.">
                      <HelpCircle size={12} />
                    </span>
                  </label>
                  <input
                    type="text"
                    disabled
                    value={meta?.drift_threshold_pct != null ? `${meta.drift_threshold_pct.toFixed(2)}%` : '5.00%'}
                    className="w-full bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none cursor-not-allowed font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="bg-white/[0.01] px-5 py-3 border-t border-white/5 text-[10px] text-gray-500">
              Embeddings similarity comparison is: <span className="font-semibold text-gray-400">{meta?.semantic_similarity_enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
          </div>

        </div>
      )}

      {activeTab === 'raw' && (
        <div className="glass rounded-xl p-5 border border-white/10 overflow-hidden">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">Config JSON Payload</span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(meta, null, 2))
                toast.success('JSON copied')
              }}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
            >
              <Copy size={11} /> Copy JSON
            </button>
          </div>
          <pre className="text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-96 bg-black/20 p-4 rounded-lg font-mono border border-white/5">
            {JSON.stringify(meta, null, 2)}
          </pre>
        </div>
      )}

      {/* Deployment / Subprocess Runner */}
      <div className="border-t border-white/10 pt-6">
        <div className="glass rounded-xl overflow-hidden border border-white/10 shadow-xl shadow-indigo-500/[0.02]">
          <div className="p-5">
            <h2 className="text-md font-bold text-gray-50 mb-1 flex items-center gap-2">
              <span>🚀</span> Prompt Version Evaluation CLI
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Select a versioned yaml prompt config to run a localized regression check against the golden dataset.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <select
                value={selectedPrompt}
                onChange={(e) => setSelectedPrompt(e.target.value)}
                className="flex-1 bg-[#12141c] border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 outline-none focus:border-indigo-500/50 transition-colors"
              >
                {prompts.map((p) => (
                  <option key={p} value={p} className="bg-[#12141c] text-gray-200">{p}</option>
                ))}
              </select>

              <button
                onClick={handleRunEval}
                disabled={running}
                className="flex items-center justify-center gap-2 bg-indigo-500 hover:bg-indigo-600 border border-indigo-500/30 text-white px-5 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {running ? (
                  <>
                    <Loader2 className="animate-spin" size={15} />
                    Evaluating...
                  </>
                ) : (
                  <>
                    <Play size={14} fill="currentColor" />
                    Deploy & Run
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal Log Console */}
      {output && (
        <div className="glass rounded-xl overflow-hidden border border-white/10 shadow-2xl shadow-black/80 fade-in-up">
          {/* Terminal Title Bar */}
          <div className="bg-[#12131a] px-4 py-2 flex items-center justify-between border-b border-white/5">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f56] border border-[#e0443e]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e] border border-[#dfa023]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#27c93f] border border-[#1aab29]" />
            </div>
            
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold font-mono">
              vercel-build-pipeline.log
            </span>

            <button
              onClick={handleCopy}
              className="text-gray-500 hover:text-gray-300 p-1 rounded hover:bg-white/5 transition-all"
              title="Copy Output Logs"
            >
              {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            </button>
          </div>

          {/* Log Outputs */}
          <div className="p-4 bg-[#08090d]/95 font-mono text-[11px] leading-relaxed max-h-[360px] overflow-y-auto space-y-3 selection:bg-indigo-500/30">
            {output.stdout && (
              <div>
                <pre className="text-gray-300 whitespace-pre-wrap select-text">
                  {output.stdout}
                </pre>
              </div>
            )}
            {output.stderr && (
              <div>
                <pre className="text-amber-300 bg-amber-500/5 border-l-2 border-amber-500/40 p-2.5 rounded whitespace-pre-wrap select-text">
                  {output.stderr}
                </pre>
              </div>
            )}
            {output.returncode !== null && (
              <div className={`mt-3 border-t border-white/5 pt-3 flex items-center justify-between ${
                output.returncode === 0 ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'
              }`}>
                <span>
                  {output.returncode === 0 
                    ? '✔ PIPELINE SUCCESS: Run status PASSED.' 
                    : `✖ PIPELINE CODE WARNING: Evaluator returned exit code ${output.returncode}.`}
                </span>
                <span className="text-[10px] bg-white/5 text-gray-500 border border-white/5 px-2 py-0.5 rounded uppercase font-mono">
                  Finished
                </span>
              </div>
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
