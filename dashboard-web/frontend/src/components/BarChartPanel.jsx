import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from 'recharts'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#12161F] border border-[#222938] rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-[#A0AEC0] mb-1 font-semibold capitalize">{label}</div>
      <div className="text-[#FFFFFF] font-extrabold">{payload[0].value.toFixed(0)}%</div>
    </div>
  )
}

export default function BarChartPanel({ data, xKey = 'name', yKey = 'value', height = 260 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 20, right: 12, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id="bar-blue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5B7FFF" stopOpacity={0.95} />
            <stop offset="100%" stopColor="#5B7FFF" stopOpacity={0.25} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: '#A0AEC0', fontSize: 11 }} axisLine={{ stroke: '#222938' }} tickLine={false} />
        <YAxis tick={{ fill: '#A0AEC0', fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
        <Bar dataKey={yKey} radius={[4, 4, 0, 0]} fill="url(#bar-blue)" animationDuration={700}>
          <LabelList dataKey={yKey} position="top" formatter={(val) => `${val.toFixed(0)}%`} fill="#A0AEC0" fontSize={11} fontWeight={600} offset={6} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
