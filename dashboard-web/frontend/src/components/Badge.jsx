const VARIANTS = {
  pass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  warning: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  fail: 'bg-red-500/15 text-red-400 border-red-500/30',
  version: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  neutral: 'bg-white/5 text-gray-300 border-white/10',
}

const STATUS_ICON = { pass: '🟢', warning: '🟡', fail: '🔴' }

export default function Badge({ variant = 'neutral', children, showIcon = false }) {
  const icon = showIcon ? STATUS_ICON[variant] : null
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${VARIANTS[variant] || VARIANTS.neutral}`}
    >
      {icon && <span>{icon}</span>}
      {children}
    </span>
  )
}

export function statusVariant(status) {
  if (status === 'PASS') return 'pass'
  if (status === 'WARNING') return 'warning'
  if (status === 'FAIL') return 'fail'
  return 'neutral'
}
