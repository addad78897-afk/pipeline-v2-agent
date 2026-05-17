import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'
import type { StepDefinition, StepState, StepStatus } from '@/utils/constants'
import { Check, Loader2, XCircle, Circle } from 'lucide-react'

interface FlowNodeProps {
  step: StepDefinition & StepState
  isActive: boolean
  onClick: () => void
  phaseColor: 'cyan' | 'magenta' | 'amber'
}

const STATUS_ICON: Record<StepStatus, typeof Circle> = {
  PENDING: Circle,
  RUNNING: Loader2,
  COMPLETED: Check,
  FAILED: XCircle,
}

const colorAccent = {
  cyan: 'var(--color-accent-cyan)',
  magenta: 'var(--color-accent-magenta)',
  amber: 'var(--color-accent-amber)',
}

export function FlowNode({ step, isActive, onClick, phaseColor }: FlowNodeProps) {
  const Icon = STATUS_ICON[step.status]
  const accent = colorAccent[phaseColor]

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.95 }}
      className={cn(
        'flex flex-col items-center gap-1.5 group',
        step.status === 'PENDING' && 'opacity-40'
      )}
    >
      {/* Node circle */}
      <div
        className={cn(
          'relative w-11 h-11 rounded-full flex items-center justify-center border-2 transition-all duration-300',
          isActive && 'animate-node-pulse'
        )}
        style={{
          borderColor:
            step.status === 'COMPLETED'
              ? accent
              : step.status === 'RUNNING'
              ? accent
              : step.status === 'FAILED'
              ? 'var(--color-accent-red)'
              : 'var(--color-border-accent)',
          backgroundColor:
            step.status === 'COMPLETED'
              ? `${accent}15`
              : step.status === 'RUNNING'
              ? `${accent}10`
              : 'transparent',
        }}
      >
        <Icon
          size={18}
          className={cn(
            step.status === 'RUNNING' && 'animate-spin',
            step.status === 'COMPLETED' && 'text-emerald-400',
            step.status === 'FAILED' && 'text-red-400',
            step.status === 'PENDING' && 'text-[var(--color-text-muted)]',
            isActive && step.status !== 'COMPLETED' && 'text-cyan-400'
          )}
        />
        {/* Active glow ring */}
        {isActive && (
          <div
            className="absolute inset-0 rounded-full animate-node-pulse opacity-30"
            style={{ border: `2px solid ${accent}` }}
          />
        )}
      </div>

      {/* Label */}
      <span className="text-[10px] text-[var(--color-text-secondary)] text-center leading-tight max-w-16">
        {step.name}
      </span>
      <span className="text-[10px] text-[var(--color-text-muted)]">Step {step.number}</span>
    </motion.button>
  )
}
