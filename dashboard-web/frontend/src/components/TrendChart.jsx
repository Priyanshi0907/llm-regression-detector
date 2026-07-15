import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, ComposedChart, Legend,
} from 'recharts'

function CustomTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null
  const displayLabel = payload[0]?.payload?.version || label
  return (
    <div className="bg-[#12161F] border border-[#222938] rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-[#A0AEC0] mb-1 font-semibold">{displayLabel}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-[#A0AEC0]">{p.name}:</span>
          <span className="text-[#FFFFFF] font-semibold">
            {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
            {unit}
          </span>
        </div>
      ))}
    </div>
  )
}

const renderCustomDot = (props) => {
  const { cx, cy, stroke } = props
  if (cx === undefined || cy === undefined) return null
  const color = stroke || '#5B7FFF'

  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill={color}
      stroke="#06070A"
      strokeWidth={1}
    />
  )
}

export default function TrendChart({ data, xKey, series, height = 280, unit = '' }) {
  const isIndex = xKey === 'index'

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: '#A0AEC0', fontSize: 11 }}
          axisLine={{ stroke: '#222938' }}
          tickLine={false}
          tickFormatter={isIndex ? (idx) => data[idx]?.version || '' : undefined}
        />
        <YAxis tick={{ fill: '#A0AEC0', fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          content={<CustomTooltip unit={unit} />}
          cursor={{ stroke: 'rgba(255, 255, 255, 0.15)', strokeWidth: 1, strokeDasharray: '3 3' }}
        />
        <Legend
          verticalAlign="top"
          align="right"
          iconType="circle"
          iconSize={6}
          formatter={(value) => <span className="text-[#A0AEC0] text-[10px] font-semibold">{value}</span>}
          wrapperStyle={{ paddingBottom: 15, top: -5 }}
        />
        {series.map((s) =>
          s.type === 'line' ? (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? '5 4' : undefined}
              dot={renderCustomDot}
              activeDot={{ r: 5, fill: s.color, stroke: '#FFFFFF', strokeWidth: 1.5 }}
              animationDuration={700}
            />
          ) : (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              fill={`url(#grad-${s.key})`}
              dot={renderCustomDot}
              activeDot={{ r: 5, fill: s.color, stroke: '#FFFFFF', strokeWidth: 1.5 }}
              animationDuration={700}
            />
          ),
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
