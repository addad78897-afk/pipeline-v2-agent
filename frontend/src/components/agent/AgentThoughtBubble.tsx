import { motion } from 'framer-motion'
import { Brain, Eye, Lightbulb, CheckCircle, Save, AlertTriangle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { AgentPhase } from '@/store/agentStore'

const cfg: Record<AgentPhase, { icon: typeof Brain; bg: string; border: string; iconColor: string; label: string }> = {
  observe:   { icon: Eye,         bg: 'bg-[var(--color-teal)]/4',   border: 'border-[var(--color-teal)]/20',   iconColor: 'text-[var(--color-teal)]',   label: '观察' },
  plan:      { icon: Lightbulb,   bg: 'bg-[var(--color-purple)]/4',  border: 'border-[var(--color-purple)]/20', iconColor: 'text-[var(--color-purple)]', label: '规划' },
  execute:   { icon: Brain,       bg: 'bg-[var(--color-orange)]/4',  border: 'border-[var(--color-orange)]/20', iconColor: 'text-[var(--color-orange)]', label: '执行' },
  verify:    { icon: CheckCircle, bg: 'bg-[var(--color-green)]/6',   border: 'border-[var(--color-green)]/20',  iconColor: 'text-[var(--color-green)]',  label: '核查' },
  record:    { icon: Save,        bg: 'bg-black/[0.03]',              border: 'border-[var(--color-border-light)]', iconColor: 'text-[var(--color-text-tertiary)]', label: '记录' },
}

interface Props { thought: string; phase: AgentPhase; timestamp: number; isLatest: boolean }

export function AgentThoughtBubble({ thought, phase, timestamp, isLatest }: Props) {
  const c = cfg[phase] ?? cfg.observe; const Icon = c.icon
  return (
    <motion.div
      initial={isLatest ? { opacity: 0, x: -16 } : false} animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
      className={cn('flex gap-3 p-4 rounded-2xl border', c.bg, c.border, isLatest && 'ring-1 ring-[var(--color-accent)]/20')}
    >
      <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center shrink-0', c.bg, c.iconColor)}><Icon size={15} /></div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-semibold text-[var(--color-text-secondary)]">{c.label}</span>
          <span className="text-[10px] text-[var(--color-text-tertiary)]">{new Date(timestamp*1000).toLocaleTimeString()}</span>
          {isLatest && <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] animate-pulse-ring" />}
        </div>
        <p className="text-[13px] text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">{thought}</p>
      </div>
    </motion.div>
  )
}

export function AgentThoughtError({ message }: { message: string }) {
  return (
    <div className="flex gap-3 p-4 rounded-2xl bg-[var(--color-red)]/6 border border-[var(--color-red)]/20">
      <AlertTriangle size={15} className="text-[var(--color-red)] shrink-0 mt-0.5" />
      <p className="text-[13px] text-[var(--color-red)]">{message}</p>
    </div>
  )
}
