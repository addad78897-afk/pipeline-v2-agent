import { motion } from 'framer-motion'
import { Check, X, Clock, RefreshCw } from 'lucide-react'
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

const phaseConfig: Record<number, { bg: string; border: string; labelBg: string; labelText: string }> = {
  1: { bg: 'bg-cyan-50', border: 'border-cyan-200', labelBg: 'bg-cyan-100', labelText: 'text-cyan-700' },
  2: { bg: 'bg-purple-50', border: 'border-purple-200', labelBg: 'bg-purple-100', labelText: 'text-purple-700' },
  3: { bg: 'bg-amber-50', border: 'border-amber-200', labelBg: 'bg-amber-100', labelText: 'text-amber-700' },
}

const statusStyles: Record<string, { bg: string; border: string }> = {
  running:   { bg: 'bg-amber-50', border: 'border-amber-200' },
  success:   { bg: 'bg-emerald-50', border: 'border-emerald-200' },
  error:     { bg: 'bg-red-50', border: 'border-red-200' },
  retrying:  { bg: 'bg-purple-50', border: 'border-purple-200' },
}

export function ToolCallCard({ toolId, toolName, phase, status, durationSeconds, outputSummary, error, isLatest }: Props) {
  const pc = phaseConfig[phase] ?? phaseConfig[1]
  const ss = statusStyles[status] ?? statusStyles.running

  return (
    <motion.div
      initial={isLatest ? { opacity: 0, scale: 0.95 } : false}
      animate={{ opacity: 1, scale: 1 }}
      className={cn('flex items-start gap-3 px-4 py-3 rounded-lg border shadow-sm transition-colors', ss.bg, ss.border)}
    >
      <div className="shrink-0 mt-0.5">
        {status === 'running' && <Clock size={14} className="text-amber-500 animate-pulse" />}
        {status === 'retrying' && <RefreshCw size={14} className="text-purple-500 animate-spin" />}
        {status === 'success' && <Check size={14} className="text-emerald-500" />}
        {status === 'error' && <X size={14} className="text-red-500" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={cn('text-[11px] px-1.5 py-0.5 rounded font-medium', pc.labelBg, pc.labelText)}>
            阶段{phase}
          </span>
          <span className="text-xs font-medium text-gray-800">{toolName}</span>
          {durationSeconds != null && (
            <span className="text-[10px] text-gray-400 ml-auto tabular-nums">{durationSeconds}s</span>
          )}
        </div>

        {outputSummary && status === 'success' && (
          <div className="mt-1.5 p-2 rounded-lg bg-white/60 border border-gray-100 text-[11px] text-gray-500 font-mono leading-relaxed line-clamp-2">
            {outputSummary}
          </div>
        )}

        {error && (
          <div className="mt-1 text-[11px] text-red-500 leading-relaxed">{error}</div>
        )}
      </div>
    </motion.div>
  )
}
