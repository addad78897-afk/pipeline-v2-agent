import { cn } from '@/utils/cn'

interface BadgeProps { status: 'PENDING'|'RUNNING'|'COMPLETED'|'FAILED'|'QUEUED'|'CANCELLED'; label?: string; className?: string }

const M: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  PENDING:   { bg: 'bg-black/[0.04]', text: 'text-[var(--color-text-tertiary)]', dot: 'bg-[var(--color-text-tertiary)]', label: '等待中' },
  RUNNING:   { bg: 'bg-[var(--color-accent)]/8', text: 'text-[var(--color-accent)]', dot: 'bg-[var(--color-accent)]', label: '运行中' },
  COMPLETED: { bg: 'bg-[var(--color-green)]/10', text: 'text-[var(--color-green)]', dot: 'bg-[var(--color-green)]', label: '已完成' },
  FAILED:    { bg: 'bg-[var(--color-red)]/8', text: 'text-[var(--color-red)]', dot: 'bg-[var(--color-red)]', label: '失败' },
  QUEUED:    { bg: 'bg-black/[0.04]', text: 'text-[var(--color-text-tertiary)]', dot: 'bg-[var(--color-text-tertiary)]', label: '排队中' },
  CANCELLED: { bg: 'bg-[var(--color-orange)]/10', text: 'text-[var(--color-orange)]', dot: 'bg-[var(--color-orange)]', label: '已取消' },
}

export function Badge({ status, label, className }: BadgeProps) {
  const s = M[status] ?? M.PENDING
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold', s.bg, s.text, className)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', s.dot, status==='RUNNING' && 'animate-pulse-ring')} />
      {label ?? s.label}
    </span>
  )
}
