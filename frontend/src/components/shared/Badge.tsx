import { cn } from '@/utils/cn'

interface BadgeProps {
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'QUEUED' | 'CANCELLED'
  label?: string
  className?: string
}

const STATUS_MAP: Record<string, { bg: string; text: string; dot: string; defaultLabel: string }> = {
  PENDING: { bg: 'bg-gray-100', text: 'text-gray-500', dot: 'bg-gray-400', defaultLabel: '等待中' },
  RUNNING: { bg: 'bg-cyan-50', text: 'text-cyan-700', dot: 'bg-cyan-500', defaultLabel: '运行中' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', defaultLabel: '已完成' },
  FAILED: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', defaultLabel: '失败' },
  QUEUED: { bg: 'bg-gray-100', text: 'text-gray-500', dot: 'bg-gray-400', defaultLabel: '排队中' },
  CANCELLED: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', defaultLabel: '已取消' },
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
