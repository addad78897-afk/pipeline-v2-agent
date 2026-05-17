import { motion } from 'framer-motion'
import { FlowNode } from './FlowNode'
import { cn } from '@/utils/cn'
import { PHASES, type StepDefinition, type StepState } from '@/utils/constants'

interface Props { steps: (StepDefinition & StepState)[]; activeStep: number; onStepClick: (s: StepDefinition & StepState) => void }

const phaseColors = {
  cyan:    { border: 'border-[var(--color-teal)]/30', bg: 'bg-[var(--color-teal)]/4', text: 'text-[var(--color-teal)]' },
  magenta: { border: 'border-[var(--color-purple)]/30', bg: 'bg-[var(--color-purple)]/4', text: 'text-[var(--color-purple)]' },
  amber:   { border: 'border-[var(--color-orange)]/30', bg: 'bg-[var(--color-orange)]/4', text: 'text-[var(--color-orange)]' },
}

export function PipelineFlow({ steps, activeStep, onStepClick }: Props) {
  return (
    <div className="space-y-6">
      {PHASES.map((phase) => {
        const ps = steps.filter((s) => phase.steps.includes(s.number))
        const colors = phaseColors[phase.color]
        const done = ps.filter((s) => s.status === 'COMPLETED').length
        return (
          <motion.div
            key={phase.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: phase.id * 0.1 }}
            className={cn('rounded-2xl border p-5', colors.border, colors.bg)}
          >
            <div className="flex items-center gap-3 mb-4">
              <span className={cn('text-[11px] font-bold px-2.5 py-1 rounded-full border', colors.border, colors.text)}>
                阶段 {phase.id}
              </span>
              <span className={cn('text-[13px] font-semibold', colors.text)}>{phase.name}</span>
              <span className="text-[12px] text-[var(--color-text-tertiary)] ml-auto">{done}/{ps.length}</span>
            </div>
            <div className="flex flex-wrap gap-3">
              {ps.map((step, i) => (
                <div key={step.number} className="flex items-center">
                  <FlowNode step={step} isActive={step.number === activeStep} onClick={() => onStepClick(step)} phaseColor={phase.color} />
                  {i < ps.length - 1 && (
                    <div className={cn('w-5 h-px mx-1 rounded', step.status === 'COMPLETED' ? 'bg-[var(--color-teal)]' : 'bg-[var(--color-border)]')} />
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
