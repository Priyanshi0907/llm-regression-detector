import { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import CommandPalette from './components/CommandPalette'
import Overview from './pages/Overview'
import Runs from './pages/Runs'
import Cases from './pages/Cases'
import Compare from './pages/Compare'
import Drift from './pages/Drift'
import HowItWorks from './pages/HowItWorks'
import DatasetUpload from './pages/DatasetUpload'
import Settings from './pages/Settings'
import Auth from './pages/Auth'
import { api } from './api'
import { Home, ListTree, FlaskConical, Scale, Activity, UploadCloud, Settings as SettingsIcon, Settings2, Bell } from 'lucide-react'

const TITLES = {
  '/': { icon: Home, title: 'Overview', subtitle: 'Monitor LLM evaluation performance and regressions' },
  '/runs': { icon: ListTree, title: 'Runs', subtitle: 'View and filter historical LLM evaluation runs' },
  '/cases': { icon: FlaskConical, title: 'Cases', subtitle: 'Inspect golden dataset test cases and metadata' },
  '/compare': { icon: Scale, title: 'Compare Runs', subtitle: 'Diff two evaluation runs side-by-side' },
  '/drift': { icon: Activity, title: 'Drift Monitor', subtitle: 'Track performance drift and rolling averages' },
  '/dataset': { icon: UploadCloud, title: 'Import Dataset', subtitle: 'Upload and parse new evaluation datasets' },
  '/settings': { icon: SettingsIcon, title: 'Settings', subtitle: 'Configure evaluation models, thresholds, and keys' },
  '/how-it-works': { icon: Settings2, title: 'How It Works', subtitle: 'Overview of evaluation methodology and scoring' },
}

function PageHeader({ user, onLogout }) {
  const loc = useLocation()
  const cfg = TITLES[loc.pathname] ?? { icon: Home, title: 'Overview', subtitle: 'Monitor LLM evaluation performance and regressions' }
  const Icon = cfg.icon

  const [notifications, setNotifications] = useState([
    { id: 1, type: 'regression', title: 'Regression Alert', desc: 'Version v8 has 3 regressions compared to v7.', time: '5 min ago', read: false },
    { id: 2, type: 'warning', title: 'Slow Drift Warning', desc: 'Moving average dropped by 0.5 pts.', time: '1 hour ago', read: false },
    { id: 3, type: 'success', title: 'Import Complete', desc: 'Golden dataset successfully updated with 60 test cases.', time: '2 hours ago', read: true }
  ])
  const [open, setOpen] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const hasUnread = notifications.some(n => !n.read)

  const getInitials = (name) => {
    if (!name) return 'AK'
    const parts = name.trim().split(/\s+/)
    return parts.map(p => p[0]).join('').slice(0, 2).toUpperCase()
  }

  return (
    <div className="flex items-center justify-between mb-8 relative">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-white/[0.02] border border-[#222938] flex items-center justify-center text-[#5B7FFF] shrink-0 mt-0.5">
          <Icon size={20} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#FFFFFF] tracking-tight">{cfg.title}</h1>
          <p className="text-xs text-[#A0AEC0] mt-0.5 font-medium">{cfg.subtitle}</p>
        </div>
      </div>
      
      {/* Right Header items: Bell & Profile avatar */}
      <div className="flex items-center gap-4 relative">
        <button
          onClick={() => setOpen(!open)}
          className="relative w-9 h-9 rounded-full bg-white/[0.02] border border-[#222938] flex items-center justify-center text-[#A0AEC0] hover:text-[#FFFFFF] transition-colors"
        >
          <Bell size={16} />
          {hasUnread && <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 bg-[#EF4444] rounded-full" />}
        </button>

        {open && (
          <div className="absolute right-12 top-11 w-80 bg-[#12161F] border border-[#222938] rounded-xl shadow-2xl z-50 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-[#222938] pb-2">
              <span className="text-xs font-bold text-white">Notifications</span>
              <button
                onClick={() => setNotifications(notifications.map(n => ({ ...n, read: true })))}
                className="text-[10px] text-[#5B7FFF] hover:underline font-semibold"
              >
                Mark all as read
              </button>
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {notifications.map((n) => {
                const iconColor = n.type === 'regression' ? 'bg-[#EF4444]/15 border-[#EF4444]/25 text-[#EF4444]' : n.type === 'warning' ? 'bg-[#F59E0B]/15 border-[#F59E0B]/25 text-[#F59E0B]' : 'bg-[#22C55E]/15 border-[#22C55E]/25 text-[#22C55E]'
                return (
                  <div
                    key={n.id}
                    onClick={() => setNotifications(notifications.map(item => item.id === n.id ? { ...item, read: true } : item))}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-colors ${n.read ? 'bg-[#0D1117]/35 border-transparent opacity-60' : 'bg-[#0D1117] border-[#222938] hover:border-[#5B7FFF]/30'}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${iconColor}`}>{n.title}</span>
                      <span className="text-[9px] text-gray-500">{n.time}</span>
                    </div>
                    <p className="text-[11px] text-gray-300 mt-1 leading-normal">{n.desc}</p>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div className="relative">
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="relative w-9 h-9 rounded-full bg-[#5B7FFF]/10 border border-[#5B7FFF]/20 flex items-center justify-center text-xs font-bold text-[#FFFFFF] uppercase font-mono hover:border-[#5B7FFF]/45 transition-colors"
          >
            {getInitials(user?.name)}
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-[#22C55E] border-2 border-[#06070A] rounded-full" />
          </button>

          {showProfileMenu && (
            <div className="absolute right-0 top-11 w-48 bg-[#12161F] border border-[#222938] rounded-xl shadow-2xl z-50 p-2 text-xs">
              <div className="px-3 py-2 border-b border-[#222938] mb-1">
                <div className="font-bold text-white truncate">{user?.name || 'Ankit Kumar'}</div>
                <div className="text-[10px] text-gray-500 truncate mt-0.5">{user?.email || 'dev@llmops.com'}</div>
              </div>
              <button
                onClick={onLogout}
                className="w-full text-left px-3 py-2 rounded-lg text-[#EF4444] hover:bg-[#EF4444]/10 transition-colors font-semibold"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Shell({ meta, runs, onOpenPalette, user, onLogout }) {
  return (
    <div className="flex min-h-screen bg-[#06070A]">
      <Sidebar meta={meta} runs={runs} onOpenPalette={onOpenPalette} />
      <main className="flex-1 px-8 py-7 max-w-[1400px] overflow-hidden">
        <PageHeader user={user} onLogout={onLogout} />
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/drift" element={<Drift />} />
          <Route path="/dataset" element={<DatasetUpload />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  const [meta, setMeta] = useState(null)
  const [runs, setRuns] = useState([])
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('llm_user')
    return saved ? JSON.parse(saved) : null
  })

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {})
    api.runs().then(setRuns).catch(() => {})
  }, [])

  const handleLogin = (u) => {
    setUser(u)
    localStorage.setItem('llm_user', JSON.stringify(u))
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('llm_user')
  }

  if (!user) {
    return (
      <>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: { background: '#171a24', color: '#e5e7eb', border: '1px solid rgba(255,255,255,0.1)', fontSize: 13 },
          }}
        />
        <Auth onLogin={handleLogin} />
      </>
    )
  }

  return (
    <HashRouter>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: { background: '#171a24', color: '#e5e7eb', border: '1px solid rgba(255,255,255,0.1)', fontSize: 13 },
        }}
      />
      <CommandPalette open={paletteOpen} onClose={setPaletteOpen} runs={runs} />
      <Shell meta={meta} runs={runs} onOpenPalette={() => setPaletteOpen(true)} user={user} onLogout={handleLogout} />
    </HashRouter>
  )
}
