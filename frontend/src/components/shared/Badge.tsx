import { cn } from '@/utils/cn'

interface BadgeProps {
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'QUEUED' | 'CANCELLED'
  label?: string
  className?: string
}

const STATUS_MAP: Record<string, { bg: string; text: string; dot: string; defaultLabel: string }> = {
  PENDING: { bg: 'bg-white/5', text: 'text-slate-400', dot: 'bg-slate-500', defaultLabel: '等待中' },
  RUNNING: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', dot: 'bg-cyan-400', defaultLabel: '运行中' },
  COMPLETED: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400', defaultLabel: '已完成' },
  FAILED: { bg: 'bg-red-500/10', text: 'text-red-400', dot: 'bg-red-400', defaultLabel: '失败' },
  QUEUED: { bg: 'bg-white/5', text: 'text-slate-400', dot: 'bg-slate-500', defaultLabel: '排队中' },
  CANCELLED: { bg: 'bg-amber-500/10', text: 'text-amber-400', dot: 'bg-amber-400', defaultLabel: '已取消' },
}

export function Badge({ status, label, className }: BadgeProps) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.PENDING
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', s.bg, s.text, className)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', s.dot, status === 'RUNNING' && 'animate-pulse-glow')} />
      {label ?? s.defaultLabel}
    </span>
  )
}
