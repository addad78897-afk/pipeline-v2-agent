import { motion } from 'framer-motion'
import { Check, X, Clock, RefreshCw, Zap, Code } from 'lucide-react'
import { cn } from '@/utils/cn'

interface Props {
  toolId: string
  toolName: string
  phase: number
  status: 'running' | 'success' | 'error' | 'retrying'
  durationSeconds?: number
  outputSummary?: string
  error?: string
  isLatest: boolean
}

const phaseColorMap: Record<number, string> = {
  1: 'cyan',
  2: 'magenta',
  3: 'amber',
}

export function ToolCallCard({ toolId, toolName, phase, status, durationSeconds, outputSummary, error, isLatest }: Props) {
  const color = phaseColorMap[phase] ?? 'slate'

  return (
    <motion.div
      initial={isLatest ? { opacity: 0, scale: 0.95 } : false}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'flex items-start gap-3 px-4 py-3 rounded-lg border transition-colors',
        status === 'running' && 'border-amber-400/20 bg-amber-500/5',
        status === 'success' && 'border-emerald-400/20 bg-emerald-500/5',
        status === 'error' && 'border-red-400/20 bg-red-500/5',
        status === 'retrying' && 'border-fuchsia-400/20 bg-fuchsia-500/5',
      )}
    >
      {/* 状态图标 */}
      <div className="shrink-0 mt-0.5">
        {status === 'running' && <Clock size={14} className="text-amber-400 animate-pulse" />}
        {status === 'retrying' && <RefreshCw size={14} className="text-fuchsia-400 animate-spin" />}
        {status === 'success' && <Check size={14} className="text-emerald-400" />}
        {status === 'error' && <X size={14} className="text-red-400" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={cn(
            'text-[11px] px-1.5 py-0.5 rounded font-medium',
            color === 'cyan' && 'bg-cyan-500/10 text-cyan-400',
            color === 'magenta' && 'bg-fuchsia-500/10 text-fuchsia-400',
            color === 'amber' && 'bg-amber-500/10 text-amber-400',
          )}>
            阶段{phase}
          </span>
          <span className="text-xs font-medium text-[var(--color-text-primary)]">
            {toolName}
          </span>
          {durationSeconds != null && (
            <span className="text-[10px] text-[var(--color-text-muted)] ml-auto tabular-nums">
              {durationSeconds}s
            </span>
          )}
        </div>

        {outputSummary && status === 'success' && (
          <div className="mt-1.5 p-2 rounded bg-black/20 text-[11px] text-[var(--color-text-muted)] font-mono leading-relaxed line-clamp-2">
            {outputSummary}
          </div>
        )}

        {error && (
          <div className="mt-1 text-[11px] text-red-400/80 leading-relaxed">
            {error}
          </div>
        )}
      </div>
    </motion.div>
  )
}
