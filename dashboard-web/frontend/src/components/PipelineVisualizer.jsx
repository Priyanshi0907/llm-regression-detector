import { FileCode, PlayCircle, Brain, ShieldCheck } from 'lucide-react'

export default function PipelineVisualizer({ version, status, totalCases }) {
  const isFail = status === 'FAIL'
  const isWarning = status === 'WARNING'
  
  const statusColor = isFail
    ? 'text-[#EF4444] border-[#EF4444]/25 bg-[#EF4444]/10'
    : isWarning
      ? 'text-[#F59E0B] border-[#F59E0B]/25 bg-[#F59E0B]/10'
      : 'text-[#22C55E] border-[#22C55E]/25 bg-[#22C55E]/10'

  const statusBorderGlow = isFail
    ? 'shadow-lg shadow-[#EF4444]/10 border-[#EF4444]/30'
    : isWarning
      ? 'shadow-lg shadow-[#F59E0B]/10 border-[#F59E0B]/30'
      : 'shadow-lg shadow-[#22C55E]/10 border-[#22C55E]/30'

  return (
    <div className="bg-[#12161F] border border-[#222938] rounded-xl p-5 mb-6 overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#5B7FFF] via-[#06B6D4] to-[#22C55E] opacity-35" />
      
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-bold text-gray-50 tracking-tight">Active Evaluation Pipeline</h4>
          <p className="text-[11px] text-gray-500">Visualizing the automated evaluation flow for prompt evals</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase ${statusColor}`}>
          <span className="relative flex h-1.5 w-1.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              isFail ? 'bg-[#EF4444]' : isWarning ? 'bg-[#F59E0B]' : 'bg-[#22C55E]'
            }`} />
            <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
              isFail ? 'bg-[#EF4444]' : isWarning ? 'bg-[#F59E0B]' : 'bg-[#22C55E]'
            }`} />
          </span>
          {status || 'PASS'} Check
        </span>
      </div>

      <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative mt-2 px-4">
        {/* Step 1: Prompt Change */}
        <div className="flex flex-col items-center text-center z-10 w-full md:w-auto">
          <div className="w-12 h-12 rounded-xl bg-[#5B7FFF]/10 border border-[#5B7FFF]/30 flex items-center justify-center shadow-lg shadow-[#5B7FFF]/5 mb-2 hover:scale-105 transition-transform">
            <FileCode size={20} className="text-[#5B7FFF] animate-pulse" />
          </div>
          <span className="text-xs font-bold text-gray-200">1. Prompt Config</span>
          <span className="text-[10px] text-gray-500 font-mono mt-0.5">{version || 'v8.yaml'}</span>
        </div>

        {/* Connector 1 */}
        <div className="hidden md:block flex-1 h-0.5 relative max-w-[80px]">
          <svg className="w-full h-2 overflow-visible" xmlns="http://www.w3.org/2000/svg">
            <line x1="0" y1="4" x2="100%" y2="4" stroke="rgba(255,255,255,0.04)" strokeWidth="2" />
            <line
              x1="0"
              y1="4"
              x2="100%"
              y2="4"
              stroke="#5B7FFF"
              strokeWidth="2"
              strokeDasharray="6 12"
              className="animate-[dash_1.5s_linear_infinite]"
            />
          </svg>
        </div>

        {/* Step 2: Runner */}
        <div className="flex flex-col items-center text-center z-10 w-full md:w-auto">
          <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center shadow-lg shadow-violet-500/5 mb-2 hover:scale-105 transition-transform">
            <PlayCircle size={20} className="text-violet-400" />
          </div>
          <span className="text-xs font-bold text-gray-200">2. Eval Runner</span>
          <span className="text-[10px] text-gray-500 mt-0.5">{totalCases || 60} Test Cases</span>
        </div>

        {/* Connector 2 */}
        <div className="hidden md:block flex-1 h-0.5 relative max-w-[80px]">
          <svg className="w-full h-2 overflow-visible" xmlns="http://www.w3.org/2000/svg">
            <line x1="0" y1="4" x2="100%" y2="4" stroke="rgba(255,255,255,0.04)" strokeWidth="2" />
            <line
              x1="0"
              y1="4"
              x2="100%"
              y2="4"
              stroke="#8b5cf6"
              strokeWidth="2"
              strokeDasharray="6 12"
              className="animate-[dash_1.5s_linear_infinite]"
            />
          </svg>
        </div>

        {/* Step 3: LLM Judge */}
        <div className="flex flex-col items-center text-center z-10 w-full md:w-auto">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shadow-lg shadow-purple-500/5 mb-2 hover:scale-105 transition-transform">
            <Brain size={20} className="text-purple-400" />
          </div>
          <span className="text-xs font-bold text-gray-200">3. LLM Rubric Judge</span>
          <span className="text-[10px] text-gray-500 mt-0.5">Semantic Scoring</span>
        </div>

        {/* Connector 3 */}
        <div className="hidden md:block flex-1 h-0.5 relative max-w-[80px]">
          <svg className="w-full h-2 overflow-visible" xmlns="http://www.w3.org/2000/svg">
            <line x1="0" y1="4" x2="100%" y2="4" stroke="rgba(255,255,255,0.04)" strokeWidth="2" />
            <line
              x1="0"
              y1="4"
              x2="100%"
              y2="4"
              stroke={isFail ? '#EF4444' : isWarning ? '#F59E0B' : '#22C55E'}
              strokeWidth="2"
              strokeDasharray="6 12"
              className="animate-[dash_1.5s_linear_infinite]"
            />
          </svg>
        </div>

        {/* Step 4: Verdict */}
        <div className="flex flex-col items-center text-center z-10 w-full md:w-auto">
          <div className={`w-12 h-12 rounded-xl bg-white/[0.01] border flex items-center justify-center mb-2 hover:scale-105 transition-transform ${statusBorderGlow}`}>
            <ShieldCheck size={20} className={
              isFail ? 'text-[#EF4444]' : isWarning ? 'text-[#F59E0B]' : 'text-[#22C55E]'
            } />
          </div>
          <span className="text-xs font-bold text-gray-200">4. CI Verdict</span>
          <span className="text-[10px] text-gray-500 mt-0.5 font-semibold">
            {isFail ? 'Merge Blocked' : isWarning ? 'Merge Warned' : 'Merge Approved'}
          </span>
        </div>
      </div>
    </div>
  )
}
