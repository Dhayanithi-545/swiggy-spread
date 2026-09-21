// Skeleton loaders. Composable bones plus ready-made card/row skeletons
// so every page's loading state looks deliberate, not blank.

export function Bone({ w = '100%', h = 14, r = 6, className = '', style }) {
  return (
    <span
      className={`bone ${className}`}
      style={{ width: w, height: h, borderRadius: r, ...style }}
      aria-hidden="true"
    />
  )
}

export function RestaurantCardSkeleton() {
  return (
    <div className="card-skel" aria-hidden="true">
      <Bone h={160} r={16} />
      <Bone w="70%" h={17} style={{ marginTop: 12 }} />
      <Bone w="45%" h={13} style={{ marginTop: 8 }} />
      <Bone w="60%" h={13} style={{ marginTop: 6 }} />
    </div>
  )
}

export function DishRowSkeleton() {
  return (
    <div className="dishrow-skel" aria-hidden="true">
      <div style={{ flex: 1 }}>
        <Bone w={14} h={14} r={3} />
        <Bone w="55%" h={16} style={{ marginTop: 8 }} />
        <Bone w={70} h={14} style={{ marginTop: 8 }} />
        <Bone w="85%" h={12} style={{ marginTop: 10 }} />
      </div>
      <Bone w={118} h={104} r={12} />
    </div>
  )
}

export function ProductCardSkeleton() {
  return (
    <div className="card-skel" aria-hidden="true">
      <Bone h={120} r={12} />
      <Bone w="80%" h={14} style={{ marginTop: 10 }} />
      <Bone w="40%" h={12} style={{ marginTop: 6 }} />
      <Bone w="55%" h={16} style={{ marginTop: 8 }} />
    </div>
  )
}

export function GridSkeleton({ count = 8, Card = RestaurantCardSkeleton, className = '' }) {
  return (
    <div className={className} role="status" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => (
        <Card key={i} />
      ))}
    </div>
  )
}
