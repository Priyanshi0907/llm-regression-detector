import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, LayoutDashboard, ListTree, FlaskConical, Scale, Activity, Settings2, UploadCloud, Settings } from 'lucide-react'

const STATIC_COMMANDS = [
  { id: 'overview', label: 'Go to Overview', icon: LayoutDashboard, path: '/' },
  { id: 'runs', label: 'Go to Runs', icon: ListTree, path: '/runs' },
  { id: 'cases', label: 'Go to Cases', icon: FlaskConical, path: '/cases' },
  { id: 'compare', label: 'Go to Compare Runs', icon: Scale, path: '/compare' },
  { id: 'drift', label: 'Go to Drift Monitor', icon: Activity, path: '/drift' },
  { id: 'dataset', label: 'Go to Import Dataset', icon: UploadCloud, path: '/dataset' },
  { id: 'settings', label: 'Go to Settings', icon: Settings, path: '/settings' },
  { id: 'how', label: 'Go to How It Works', icon: Settings2, path: '/how-it-works' },
]

export default function CommandPalette({ open, onClose, runs = [] }) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) setQuery('')
  }, [open])

  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        onClose(!open)
      }
      if (e.key === 'Escape') onClose(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const runCommands = useMemo(
    () =>
      runs.slice(0, 8).map((r) => ({
        id: r.run_id,
        label: `Run ${r.run_id} · ${r.prompt_version} · ${r.status}`,
        icon: ListTree,
        path: `/runs?open=${encodeURIComponent(r.run_id)}`,
      })),
    [runs],
  )

  const all = [...STATIC_COMMANDS, ...runCommands]
  const filtered = query
    ? all.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : all

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm"
      onClick={() => onClose(false)}
    >
      <div
        className="glass w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
          <Search size={16} className="text-gray-500" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Jump to a page or run…"
            className="bg-transparent outline-none flex-1 text-sm placeholder:text-gray-500"
          />
          <kbd className="text-[10px] text-gray-500 border border-white/10 rounded px-1.5 py-0.5">esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto py-2">
          {filtered.length === 0 && (
            <div className="px-4 py-6 text-sm text-gray-500 text-center">No matches</div>
          )}
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => {
                navigate(c.path)
                onClose(false)
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-white/5 transition-colors text-left"
            >
              <c.icon size={15} className="text-gray-500 shrink-0" />
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
