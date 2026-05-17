import { cn } from '@/utils/cn'

export function LoadingSkeleton({ className, rows = 3 }: { className?: string; rows?: number }) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton rounded-lg" style={{ height: `${20 + Math.random() * 12}px`, width: `${60 + Math.random() * 40}%` }} />
      ))}
    </div>
  )
}

export function EmptyState({ icon, title, description }: { icon?: string; title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-4xl mb-4 opacity-40">{icon}</div>}
      <h3 className="text-lg font-medium text-[var(--color-text-secondary)] mb-1">{title}</h3>
      {description && <p className="text-sm text-[var(--color-text-muted)] max-w-md">{description}</p>}
    </div>
  )
}
