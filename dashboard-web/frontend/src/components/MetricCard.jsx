export default function MetricCard({ icon: Icon, label, value, delta, trend, status, subtitle }) {
  const isFail = status === 'fail' || status === 'FAIL'
  const isWarning = status === 'warning' || status === 'WARNING'
  const isPass = status === 'pass' || status === 'PASS'

  const themeClasses = isFail
    ? 'bg-[#EF4444]/5 border-[#EF4444]/25 text-[#EF4444]'
    : isWarning
      ? 'bg-[#F59E0B]/5 border-[#F59E0B]/25 text-[#F59E0B]'
      : isPass
        ? 'bg-[#22C55E]/5 border-[#22C55E]/25 text-[#22C55E]'
        : 'bg-[#5B7FFF]/5 border-[#5B7FFF]/25 text-[#5B7FFF]'

  const deltaTextClass = trend === 'good'
    ? 'text-[#22C55E]'
    : trend === 'bad'
      ? 'text-[#EF4444]'
      : 'text-[#A0AEC0]'

  const isStatusLabel = label?.toLowerCase()?.includes('status')
  const valueColorClass = isStatusLabel
    ? (isFail ? 'text-[#EF4444]' : isWarning ? 'text-[#F59E0B]' : isPass ? 'text-[#22C55E]' : 'text-[#FFFFFF]')
    : 'text-[#FFFFFF]'

  const subtitleColorClass = isStatusLabel ? valueColorClass : 'text-[#A0AEC0]/85 font-medium'

  return (
    <div className="bg-[#12161F] border border-[#222938] rounded-xl p-5 flex items-center gap-5 transition-all duration-300 hover:border-[#5B7FFF]/30">
      {Icon && (
        <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 border ${themeClasses}`}>
          <Icon size={20} className="opacity-95" />
        </div>
      )}
      
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-bold text-[#A0AEC0] uppercase tracking-wider">
          {label}
        </div>
        <div className={`text-2xl font-extrabold mt-0.5 tracking-tight flex items-center gap-2 ${valueColorClass}`}>
          {value}
        </div>
        {(delta || subtitle) && (
          <div className="mt-1 flex items-center gap-1.5 text-[11px] font-semibold text-gray-500 font-sans">
            {delta && (
              <span className={deltaTextClass}>
                {delta}
              </span>
            )}
            {delta && subtitle && <span className="opacity-40">·</span>}
            {subtitle && <span className={subtitleColorClass}>{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  )
}
