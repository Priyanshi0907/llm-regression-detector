export function CardSkeleton() {
  return (
    <div className="glass rounded-xl p-4">
      <div className="skeleton h-3 w-20 mb-3" />
      <div className="skeleton h-7 w-16" />
    </div>
  )
}

export function ChartSkeleton({ height = 280 }) {
  return <div className="skeleton rounded-xl w-full" style={{ height }} />
}

export function RowSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-10 w-full" />
      ))}
    </div>
  )
}

export function GridSkeleton({ count = 4 }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}
