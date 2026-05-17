import { X, Clock, FileCode, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/shared/Badge'
import type { StepDefinition, StepState } from '@/utils/constants'

interface StepDetailPanelProps {
  step: StepDefinition
  stepState: StepState
  onClose: () => void
}

export function StepDetailPanel({ step, stepState, onClose }: StepDetailPanelProps) {
  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 20 }}
        className="w-80 shrink-0 border-l border-[var(--color-border)] bg-[var(--color-bg-secondary)] overflow-auto"
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-4">
            <Badge status={stepState.status} />
            <button onClick={onClose} className="p-1 rounded hover:bg-white/10 text-[var(--color-text-muted)]">
              <X size={16} />
            </button>
          </div>

          <h3 className="text-sm font-semibold mb-1">{step.name}</h3>
          <div className="text-xs text-[var(--color-text-muted)] mb-4">Step {step.number} · {step.script}</div>

          <div className="glass p-3 mb-4">
            <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{step.description}</p>
          </div>

          {stepState.startedAt && (
            <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] mb-2">
              <Clock size={12} />
              开始：{new Date(stepState.startedAt).toLocaleTimeString()}
            </div>
          )}
          {stepState.completedAt && (
            <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] mb-2">
              <Clock size={12} />
              完成：{new Date(stepState.completedAt).toLocaleTimeString()}
            </div>
          )}

          {stepState.error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-400/20">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-400">{stepState.error}</p>
            </div>
          )}

          {stepState.log.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] mb-2">
                <FileCode size={12} />
                输出日志
              </div>
              <div className="glass p-3 font-mono text-[11px] text-[var(--color-text-secondary)] max-h-48 overflow-auto space-y-0.5">
                {stepState.log.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  )
}
