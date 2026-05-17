import { motion } from 'framer-motion'
import { Brain, Eye, Lightbulb, CheckCircle, Save, AlertTriangle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { AgentPhase } from '@/store/agentStore'

const phaseConfig: Record<AgentPhase, { icon: typeof Brain; bg: string; border: string; label: string }> = {
  observe:   { icon: Eye,           bg: 'bg-cyan-500/5',  border: 'border-cyan-400/20',  label: '观察' },
  plan:      { icon: Lightbulb,     bg: 'bg-fuchsia-500/5', border: 'border-fuchsia-400/20', label: '规划' },
  execute:   { icon: Brain,         bg: 'bg-amber-500/5',   border: 'border-amber-400/20',  label: '执行' },
  verify:    { icon: CheckCircle,   bg: 'bg-emerald-500/5', border: 'border-emerald-400/20', label: '核查' },
  record:    { icon: Save,          bg: 'bg-slate-500/5',   border: 'border-slate-400/20',  label: '记录' },
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
        'flex gap-3 p-4 rounded-xl border text-sm',
        cfg.bg, cfg.border,
        isLatest && 'ring-1 ring-white/10'
      )}
    >
      <div className={cn(
        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
        phase === 'observe' ? 'bg-cyan-500/10 text-cyan-400' :
        phase === 'plan' ? 'bg-fuchsia-500/10 text-fuchsia-400' :
        phase === 'verify' ? 'bg-emerald-500/10 text-emerald-400' :
        phase === 'execute' ? 'bg-amber-500/10 text-amber-400' :
        'bg-slate-500/10 text-slate-400'
      )}>
        <Icon size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-medium text-[var(--color-text-muted)]">{cfg.label}</span>
          <span className="text-[10px] text-[var(--color-text-muted)]/50">
            {new Date(timestamp * 1000).toLocaleTimeString()}
          </span>
          {isLatest && (
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          )}
        </div>
        <p className="text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">{thought}</p>
      </div>
    </motion.div>
  )
}

export function AgentThoughtError({ message }: { message: string }) {
  return (
    <div className="flex gap-3 p-4 rounded-xl border bg-red-500/5 border-red-400/20">
      <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
      <p className="text-sm text-red-400">{message}</p>
    </div>
  )
}
