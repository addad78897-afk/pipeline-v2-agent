interface Props { className?: string; rows?: number }

export function LoadingSkeleton({ className, rows = 3 }: Props) {
  return (
    <div className={`space-y-3 ${className??''}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: `${16 + Math.random()*8}px`, width: `${55 + Math.random()*45}%` }} />
      ))}
    </div>
  )
}

export function EmptyState({ icon, title, description }: { icon?: string; title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-3xl mb-3 opacity-40">{icon}</div>}
      <h3 className="text-[15px] font-semibold text-[var(--color-text-secondary)] mb-1">{title}</h3>
      {description && <p className="text-[13px] text-[var(--color-text-tertiary)] max-w-md">{description}</p>}
    </div>
  )
}
