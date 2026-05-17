import { X, Clock, FileCode, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/shared/Badge'
import type { StepDefinition, StepState } from '@/utils/constants'

interface Props { step: StepDefinition; stepState: StepState; onClose: () => void }

export function StepDetailPanel({ step, stepState, onClose }: Props) {
  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 22 }}
        className="w-80 shrink-0 border-l border-[var(--color-border-light)] bg-white overflow-auto"
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-4">
            <Badge status={stepState.status} />
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-black/[0.04] text-[var(--color-text-tertiary)]">
              <X size={16} />
            </button>
          </div>
          <h3 className="text-[15px] font-semibold mb-1">{step.name}</h3>
          <div className="text-[12px] text-[var(--color-text-tertiary)] mb-4">Step {step.number} · {step.script}</div>
          <div className="bg-[var(--color-bg-primary)] rounded-xl p-3 mb-4">
            <p className="text-[12px] text-[var(--color-text-secondary)] leading-relaxed">{step.description}</p>
          </div>
          {stepState.startedAt && <div className="flex items-center gap-2 text-[12px] text-[var(--color-text-tertiary)] mb-1.5"><Clock size={12} />开始 {new Date(stepState.startedAt).toLocaleTimeString()}</div>}
          {stepState.completedAt && <div className="flex items-center gap-2 text-[12px] text-[var(--color-text-tertiary)] mb-1.5"><Clock size={12} />完成 {new Date(stepState.completedAt).toLocaleTimeString()}</div>}
          {stepState.error && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-[var(--color-red)]/6">
              <AlertCircle size={14} className="text-[var(--color-red)] shrink-0 mt-0.5" />
              <p className="text-[12px] text-[var(--color-red)]">{stepState.error}</p>
            </div>
          )}
          {stepState.log.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center gap-2 text-[12px] text-[var(--color-text-tertiary)] mb-2"><FileCode size={12} />输出日志</div>
              <div className="bg-[var(--color-bg-primary)] rounded-xl p-3 font-mono text-[11px] text-[var(--color-text-secondary)] max-h-48 overflow-auto">
                {stepState.log.map((l, i) => <div key={i}>{l}</div>)}
              </div>
            </div>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  )
}
