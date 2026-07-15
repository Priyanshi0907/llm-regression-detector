import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, ListTree, FlaskConical, Scale, Activity, Settings2,
  ChevronsLeft, ChevronsRight, Command, BarChart3, UploadCloud, Settings, Search,
} from 'lucide-react'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/runs', label: 'Runs', icon: ListTree },
  { to: '/cases', label: 'Cases', icon: FlaskConical },
  { to: '/compare', label: 'Compare Runs', icon: Scale },
  { to: '/drift', label: 'Drift Monitor', icon: Activity },
  { to: '/dataset', label: 'Import Dataset', icon: UploadCloud },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/how-it-works', label: 'How It Works', icon: Settings2 },
]

export default function Sidebar({ meta, runs, onOpenPalette }) {
  const [collapsed, setCollapsed] = useState(false)
  const isMock = meta?.mock_mode

  return (
    <aside
      className={`h-screen sticky top-0 shrink-0 border-r border-[#222938] bg-[#06070A] flex flex-col transition-all duration-200 ${
        collapsed ? 'w-[68px]' : 'w-64'
      }`}
    >
      <div className="flex items-center gap-2.5 px-4 py-5">
        <div className="w-8 h-8 rounded-lg bg-[#5B7FFF] flex items-center justify-center shrink-0 shadow-lg shadow-[#5B7FFF]/20">
          <BarChart3 size={17} className="text-white" strokeWidth={2.5} />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <div className="font-bold text-sm text-[#FFFFFF] leading-tight whitespace-nowrap tracking-tight">
              LLM Regression Detector
            </div>
            <div className="text-[11px] text-[#A0AEC0] whitespace-nowrap font-medium">LLMops for reliable releases</div>
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="px-4 mb-4">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            Demo Mode
          </span>
        </div>
      )}

      <button
        onClick={onOpenPalette}
        className={`mx-4 mb-4 flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-[#222938] bg-[#0D1117] text-[#A0AEC0] hover:text-[#FFFFFF] hover:border-white/10 transition-colors text-xs ${
          collapsed ? 'justify-center' : 'justify-between'
        }`}
      >
        {!collapsed && (
          <span className="flex items-center gap-2 font-medium">
            <Search size={13} className="text-[#A0AEC0]/60" /> Search
          </span>
        )}
        {collapsed ? <Search size={14} /> : <kbd className="text-[10px] opacity-75 font-mono">⌘K</kbd>}
      </button>

      <nav className="flex-1 px-2.5 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors group ${
                isActive
                  ? 'bg-[#5B7FFF]/10 text-[#5B7FFF] font-semibold'
                  : 'text-[#A0AEC0] hover:text-[#FFFFFF] hover:bg-white/5'
              }`
            }
            title={collapsed ? item.label : undefined}
          >
            <item.icon size={16} className="shrink-0" />
            {!collapsed && <span className="whitespace-nowrap font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {!collapsed && runs?.length > 0 && (
        <div className="px-4 py-4 border-t border-[#222938] mt-auto">
          <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2.5">
            Recent Runs
          </div>
          <div className="space-y-2">
            {runs.slice(0, 4).map((r) => (
              <NavLink
                key={r.run_id}
                to={`/runs?open=${r.run_id}`}
                className="flex items-center justify-between text-xs text-[#A0AEC0] hover:text-[#FFFFFF] transition-colors"
              >
                <div className="flex gap-3 font-mono text-[11px]">
                  <span className="font-bold text-gray-400">{r.prompt_version}</span>
                  <span className="text-gray-500">{r.run_id}</span>
                </div>
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    r.status === 'PASS' || r.status === 'pass'
                      ? 'bg-[#22C55E]'
                      : r.status === 'WARNING' || r.status === 'warning'
                        ? 'bg-[#F59E0B]'
                        : 'bg-[#EF4444]'
                  }`}
                />
              </NavLink>
            ))}
          </div>
          <NavLink
            to="/runs"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#5B7FFF] hover:underline mt-3"
          >
            View all runs →
          </NavLink>
        </div>
      )}

      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center gap-2 px-4 py-3 border-t border-[#222938] text-[#A0AEC0] hover:text-[#FFFFFF] transition-colors text-xs"
      >
        {collapsed ? <ChevronsRight size={15} /> : (<><ChevronsLeft size={15} /> Collapse</>)}
      </button>
    </aside>
  )
}
