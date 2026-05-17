import { motion } from 'framer-motion'
import { Brain, Eye, Lightbulb, CheckCircle, Save, AlertTriangle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { AgentPhase } from '@/store/agentStore'

const phaseConfig: Record<AgentPhase, { icon: typeof Brain; bg: string; border: string; iconColor: string; label: string }> = {
  observe:   { icon: Eye,         bg: 'bg-cyan-50',    border: 'border-cyan-200',    iconColor: 'text-cyan-600',   label: '观察' },
  plan:      { icon: Lightbulb,   bg: 'bg-purple-50',   border: 'border-purple-200',  iconColor: 'text-purple-600', label: '规划' },
  execute:   { icon: Brain,       bg: 'bg-amber-50',    border: 'border-amber-200',   iconColor: 'text-amber-600',  label: '执行' },
  verify:    { icon: CheckCircle, bg: 'bg-emerald-50',  border: 'border-emerald-200', iconColor: 'text-emerald-600', label: '核查' },
  record:    { icon: Save,        bg: 'bg-gray-50',     border: 'border-gray-200',    iconColor: 'text-gray-500',   label: '记录' },
}

interface Props {
  thought: string
  phase: AgentPhase
  timestamp: number
  isLatest: boolean
}

export function AgentThoughtBubble({ thought, phase, timestamp, isLatest }: Props) {
  const cfg = phaseConfig[phase] ?? phaseConfig.observe
  const Icon = cfg.icon

  return (
    <motion.div
      initial={isLatest ? { opacity: 0, x: -20 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'flex gap-3 p-4 rounded-xl border text-sm shadow-sm',
        cfg.bg, cfg.border,
        isLatest && 'ring-2 ring-cyan-200'
      )}
    >
      <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0', cfg.bg, cfg.iconColor)}>
        <Icon size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-medium text-gray-500">{cfg.label}</span>
          <span className="text-[10px] text-gray-400">
            {new Date(timestamp * 1000).toLocaleTimeString()}
          </span>
          {isLatest && (
            <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
          )}
        </div>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{thought}</p>
      </div>
    </motion.div>
  )
}

export function AgentThoughtError({ message }: { message: string }) {
  return (
    <div className="flex gap-3 p-4 rounded-xl border bg-red-50 border-red-200">
      <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
      <p className="text-sm text-red-600">{message}</p>
    </div>
  )
}
