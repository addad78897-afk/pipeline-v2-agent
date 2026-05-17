import { motion } from 'framer-motion'
import { FlowNode } from './FlowNode'
import { cn } from '@/utils/cn'
import { PHASES, type StepDefinition, type StepState } from '@/utils/constants'

interface PipelineFlowProps {
  steps: (StepDefinition & StepState)[]
  activeStep: number
  onStepClick: (step: StepDefinition & StepState) => void
}

const colorMap = {
  cyan: { border: 'border-cyan-400/30', bg: 'bg-cyan-500/5', text: 'text-cyan-400', glow: 'glow-cyan' },
  magenta: { border: 'border-fuchsia-400/30', bg: 'bg-fuchsia-500/5', text: 'text-fuchsia-400', glow: 'glow-magenta' },
  amber: { border: 'border-amber-400/30', bg: 'bg-amber-500/5', text: 'text-amber-400', glow: 'glow-amber' },
}

export function PipelineFlow({ steps, activeStep, onStepClick }: PipelineFlowProps) {
  return (
    <div className="space-y-8">
      {PHASES.map((phase) => {
        const phaseSteps = steps.filter((s) => phase.steps.includes(s.number))
        const colors = colorMap[phase.color]
        const completedCount = phaseSteps.filter((s) => s.status === 'COMPLETED').length

        return (
          <motion.div
            key={phase.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: phase.id * 0.15 }}
            className={cn('rounded-2xl border p-5', colors.border, colors.bg)}
          >
            <div className="flex items-center gap-3 mb-4">
              <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full border', colors.border, colors.text)}>
                阶段 {phase.id}
              </span>
              <span className={cn('text-sm font-medium', colors.text)}>{phase.name}</span>
              <span className="text-xs text-[var(--color-text-muted)] ml-auto">
                {completedCount}/{phaseSteps.length} 完成
              </span>
            </div>

            <div className="flex flex-wrap gap-3">
              {phaseSteps.map((step, i) => (
                <div key={step.number} className="flex items-center">
                  <FlowNode
                    step={step}
                    isActive={step.number === activeStep}
                    onClick={() => onStepClick(step)}
                    phaseColor={phase.color}
                  />
                  {i < phaseSteps.length - 1 && (
                    <div className={cn('w-6 h-0.5 mx-1 rounded', step.status === 'COMPLETED' ? 'bg-cyan-400/50' : 'bg-white/10')} />
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
