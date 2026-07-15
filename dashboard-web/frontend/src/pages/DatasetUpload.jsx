import { useState } from 'react'
import toast from 'react-hot-toast'
import { UploadCloud, FileText } from 'lucide-react'
import { api } from '../api'

function analyzeFileContent(text, name) {
  const isJson = name.toLowerCase().endsWith('.json')
  let rows = []
  let schemaErrors = []
  let duplicates = 0
  let diffMix = { easy: 0, medium: 0, hard: 0 }

  try {
    if (isJson) {
      const data = JSON.parse(text)
      rows = Array.isArray(data) ? data : [data]
      rows.forEach(r => {
        if (!r.id) schemaErrors.push('Missing unique ID in some JSON rows')
      })
    } else {
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
      if (lines.length > 1) {
        const header = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''))
        const required = ['id', 'input', 'expected_category', 'expected_summary']
        required.forEach(col => {
          if (!header.includes(col)) {
            schemaErrors.push(`Missing required column: ${col}`)
          }
        })

        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/)
          const id = cols[header.indexOf('id')]?.replace(/"/g, '') || ''
          const difficulty = cols[header.indexOf('expected_difficulty')]?.replace(/"/g, '').toLowerCase() || ''
          rows.push({ id, difficulty })
        }
      } else {
        schemaErrors.push('CSV file contains no rows or header row only')
      }
    }

    const ids = rows.map(r => r.id).filter(Boolean)
    duplicates = ids.length - new Set(ids).size

    rows.forEach(r => {
      const diff = r.difficulty || 'medium'
      if (diff === 'easy') diffMix.easy++
      else if (diff === 'hard') diffMix.hard++
      else diffMix.medium++
    })

    return {
      success: schemaErrors.length === 0,
      totalRows: rows.length,
      duplicates,
      schemaErrors,
      diffMix
    }
  } catch (e) {
    return {
      success: false,
      totalRows: 0,
      duplicates: 0,
      schemaErrors: ['File could not be parsed: ' + e.message],
      diffMix: { easy: 0, medium: 0, hard: 0 }
    }
  }
}

export default function DatasetUpload() {
  const [file, setFile] = useState(null)
  const [content, setContent] = useState('')
  const [filename, setFilename] = useState('')
  const [outputPath, setOutputPath] = useState('golden_dataset/dataset_imported.json')
  const [mergeWith, setMergeWith] = useState('golden_dataset/dataset_v1.json')
  const [doMerge, setDoMerge] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [validation, setValidation] = useState(null)
  const [progress, setProgress] = useState(0)

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setFilename(f.name)
    const reader = new FileReader()
    reader.onload = () => {
      setContent(reader.result)
      const analysis = analyzeFileContent(reader.result, f.name)
      setValidation(analysis)
    }
    reader.readAsText(f)
  }

  async function handleSubmit() {
    if (!content || !filename) {
      toast.error('Choose a CSV or JSON file first')
      return
    }
    setSubmitting(true)
    setProgress(15)
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 85) return p
        return p + 10
      })
    }, 120)

    try {
      const res = await api.uploadDataset({
        content,
        filename,
        output_path: outputPath,
        merge_with: doMerge ? mergeWith : null,
      })
      setProgress(100)
      setResult(res)
      toast.success(`Imported ${res.total_cases} cases (${res.added} added, ${res.updated} updated)`)
    } catch (e) {
      toast.error(`Import failed: ${e.message}`)
    } finally {
      clearInterval(interval)
      setSubmitting(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left Column: Upload and Setup */}
      <div className="space-y-6">
        <div className="glass rounded-xl p-5 space-y-5">
          <div>
            <h3 className="text-sm font-semibold text-gray-250 mb-1">Import real test cases</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Replaces the "demo data only" limitation — upload a CSV or JSON file of real
              production cases. Every row is validated against the same schema the eval engine uses.
            </p>
          </div>

          <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-[#222938] hover:border-[#5B7FFF]/40 rounded-xl py-10 cursor-pointer bg-[#0D1117]/30 transition-colors">
            <input type="file" accept=".csv,.json" className="hidden" onChange={handleFile} />
            <UploadCloud size={28} className="text-[#A0AEC0] animate-pulse" />
            <span className="text-xs text-gray-400 font-semibold mt-1">
              {filename || 'Drag & drop or click to choose a .csv or .json file'}
            </span>
          </label>

          {content && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs text-gray-400 font-mono bg-[#0D1117] p-2 rounded border border-[#222938]">
                <FileText size={14} className="text-[#5B7FFF]" /> {filename} — {content.split('\n').length} rows loaded
              </div>

              {/* Client-side Validation Report */}
              {validation && (
                <div className="bg-[#12161F]/80 border border-[#222938] rounded-xl p-4 space-y-3.5">
                  <h4 className="text-xs font-semibold text-gray-450 uppercase tracking-wider">Pre-Import Validation</h4>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-[#0D1117] p-2.5 rounded border border-[#222938]">
                      <span className="text-gray-500 block text-[9px] font-bold uppercase mb-0.5">Parse Schema</span>
                      <span className={validation.success ? 'text-[#22C55E] font-bold' : 'text-[#EF4444] font-bold'}>
                        {validation.success ? '✅ VALID SCHEMA' : '❌ SCHEMAS MISMATCH'}
                      </span>
                    </div>
                    <div className="bg-[#0D1117] p-2.5 rounded border border-[#222938]">
                      <span className="text-gray-500 block text-[9px] font-bold uppercase mb-0.5">Duplicates Detected</span>
                      <span className={validation.duplicates > 0 ? 'text-[#F59E0B] font-bold' : 'text-[#22C55E] font-bold'}>
                        {validation.duplicates > 0 ? `⚠️ ${validation.duplicates} DUPLICATES` : '✅ NONE'}
                      </span>
                    </div>
                  </div>

                  {validation.schemaErrors.length > 0 && (
                    <div className="bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-lg p-2.5 text-xs text-[#EF4444] space-y-1">
                      {validation.schemaErrors.map((err, i) => <div key={i}>• {err}</div>)}
                    </div>
                  )}

                  <div className="text-xs text-gray-400 space-y-1 bg-[#0D1117]/30 p-2.5 rounded border border-[#222938] font-mono text-[10px]">
                    <div className="flex justify-between"><span>Row Count Preview:</span> <span className="text-white font-bold">{validation.totalRows}</span></div>
                    <div className="flex justify-between"><span>Difficulty Mix:</span> <span>Easy: {validation.diffMix.easy} · Med: {validation.diffMix.medium} · Hard: {validation.diffMix.hard}</span></div>
                  </div>
                </div>
              )}

              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block mb-1">Output Path</label>
                <input
                  value={outputPath}
                  onChange={(e) => setOutputPath(e.target.value)}
                  className="w-full bg-[#0D1117] border border-[#222938] rounded-lg px-3 py-2 text-sm text-gray-200 outline-none focus:border-[#5B7FFF]/40 transition-colors"
                />
              </div>

              <label className="flex items-center gap-2 text-xs text-gray-400 font-semibold cursor-pointer">
                <input type="checkbox" checked={doMerge} onChange={(e) => setDoMerge(e.target.checked)} className="rounded border-[#222938] text-[#5B7FFF]" />
                Merge with existing evaluation dataset
              </label>

              {doMerge && (
                <input
                  value={mergeWith}
                  onChange={(e) => setMergeWith(e.target.value)}
                  className="w-full bg-[#0D1117] border border-[#222938] rounded-lg px-3 py-2 text-sm text-gray-200 outline-none focus:border-[#5B7FFF]/40 transition-colors"
                  placeholder="Path to existing dataset JSON"
                />
              )}

              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="w-full bg-[#5B7FFF] hover:bg-[#5B7FFF]/95 text-white rounded-lg py-2.5 text-xs font-bold transition-colors disabled:opacity-50"
              >
                {submitting ? 'Importing…' : 'Import Dataset'}
              </button>

              {submitting && (
                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                    <span>Importing cases into database...</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-[#5B7FFF] transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {result && (
          <div className="bg-[#22C55E]/10 border border-[#22C55E]/20 rounded-xl p-4 space-y-2.5 fade-in-up">
            <div className="text-xs text-[#22C55E] font-bold uppercase tracking-wider">✅ Dataset Successfully Imported</div>
            <div className="grid grid-cols-3 gap-2.5 text-xs pt-1">
              <div className="bg-[#0D1117]/60 p-2 rounded text-center border border-[#22C55E]/15">
                <span className="text-gray-550 text-[9px] uppercase block font-mono">Total Cases</span>
                <span className="font-bold text-white font-mono text-sm">{result.total_cases}</span>
              </div>
              <div className="bg-[#0D1117]/60 p-2 rounded text-center border border-[#22C55E]/15">
                <span className="text-gray-550 text-[9px] uppercase block font-mono">Added</span>
                <span className="font-bold text-emerald-400 font-mono text-sm">+{result.added}</span>
              </div>
              <div className="bg-[#0D1117]/60 p-2 rounded text-center border border-[#22C55E]/15">
                <span className="text-gray-550 text-[9px] uppercase block font-mono">Updated</span>
                <span className="font-bold text-indigo-400 font-mono text-sm">~{result.updated}</span>
              </div>
            </div>
            <p className="text-[10px] text-gray-500 leading-normal pt-1.5 border-t border-[#222938]/40">
              Golden database saved to <code className="text-gray-300 font-mono">{result.output_path}</code>.
            </p>
          </div>
        )}

        <div className="glass rounded-xl p-4">
          <h4 className="text-xs font-semibold text-gray-450 uppercase mb-2">Expected CSV schema</h4>
          <code className="text-[11px] text-[#A0AEC0] block bg-black/30 rounded-lg p-3 border border-[#222938] mono whitespace-normal">
            id, input, expected_category, expected_summary, expected_difficulty, notes
          </code>
          <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">
            Note: <code className="text-gray-400 font-mono">expected_category</code> must match the category enums: <code className="text-gray-400 font-mono">billing, technical, account, general</code>.
            Difficulty levels must be <code className="text-gray-400 font-mono">easy, medium, or hard</code>.
          </p>
        </div>
      </div>

      {/* Right Column: Sandbox Dataset Preview */}
      <div className="glass rounded-xl p-5 flex flex-col h-full border border-[#222938]">
        <div>
          <h3 className="text-sm font-semibold text-gray-250 mb-1">Dataset Sandbox Preview</h3>
          <p className="text-xs text-gray-500 mb-4">
            Verify your import structure against this high-fidelity golden dataset preview.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 max-h-[500px]">
          {[
            {
              id: 'TC001',
              category: 'billing',
              difficulty: 'easy',
              input: 'Hi, I received my monthly invoice but it shows a double charge of $49 for the subscription. Can you verify and issue a refund?',
              summary: 'Requesting refund for $49 double monthly subscription charge'
            },
            {
              id: 'TC002',
              category: 'technical',
              difficulty: 'medium',
              input: 'Getting a 502 Bad Gateway error whenever I try to call the classification API via the Python SDK. Please assist.',
              summary: 'Python classification SDK endpoint returns 502 Bad Gateway'
            },
            {
              id: 'TC003',
              category: 'account',
              difficulty: 'hard',
              input: 'I lost access to my MFA token and can no longer login to the admin workspace. I need an administrator to reset it.',
              summary: 'Requesting administrative reset for lost MFA authenticator token'
            }
          ].map((item) => {
            const diffColor = item.difficulty === 'easy' ? 'text-[#22C55E] bg-[#22C55E]/10 border-[#22C55E]/20' : item.difficulty === 'medium' ? 'text-[#5B7FFF] bg-[#5B7FFF]/10 border-[#5B7FFF]/20' : 'text-[#EF4444] bg-[#EF4444]/10 border-[#EF4444]/20'
            return (
              <div key={item.id} className="bg-[#0D1117]/35 border border-[#222938] rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold bg-[#5B7FFF]/15 text-[#5B7FFF] border border-[#5B7FFF]/25 px-2 py-0.5 rounded font-mono uppercase">{item.id}</span>
                    <span className="text-[10px] font-bold bg-white/5 border border-white/10 px-2 py-0.5 rounded uppercase text-gray-400">{item.category}</span>
                  </div>
                  <span className={`text-[9px] font-bold border px-1.5 py-0.5 rounded uppercase font-mono ${diffColor}`}>{item.difficulty}</span>
                </div>
                <div className="text-xs text-gray-300 line-clamp-2 leading-relaxed">
                  <span className="text-gray-500 font-bold block uppercase text-[9px] mb-0.5">Input Email</span>
                  "{item.input}"
                </div>
                <div className="text-xs text-gray-400 leading-relaxed pt-1.5 border-t border-[#222938]/40">
                  <span className="text-gray-500 font-bold block uppercase text-[9px] mb-0.5">Expected Summary</span>
                  "{item.summary}"
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
