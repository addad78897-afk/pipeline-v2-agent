import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'
import type { StepDefinition, StepState, StepStatus } from '@/utils/constants'
import { Check, Loader2, XCircle, Circle } from 'lucide-react'

interface Props { step: StepDefinition & StepState; isActive: boolean; onClick: () => void; phaseColor: 'cyan'|'magenta'|'amber' }

const accentColor = { cyan: 'var(--color-teal)', magenta: 'var(--color-purple)', amber: 'var(--color-orange)' }

const IconMap: Record<StepStatus, typeof Circle> = { PENDING: Circle, RUNNING: Loader2, COMPLETED: Check, FAILED: XCircle }

export function FlowNode({ step, isActive, onClick, phaseColor }: Props) {
  const Icon = IconMap[step.status]
  const accent = accentColor[phaseColor]

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.95 }}
      className={cn('flex flex-col items-center gap-1 group', step.status === 'PENDING' && 'opacity-50')}
    >
      <div
        className={cn('relative w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all', isActive && 'animate-pulse-ring')}
        style={{
          borderColor: step.status === 'COMPLETED' ? accent
            : step.status === 'RUNNING' ? accent
            : step.status === 'FAILED' ? 'var(--color-red)'
            : 'var(--color-border)',
          backgroundColor: step.status === 'COMPLETED' ? `${accent}18`
            : step.status === 'RUNNING' ? `${accent}0C`
            : 'transparent',
        }}
      >
        <Icon size={16} className={cn(
          step.status === 'RUNNING' && 'animate-spin',
          step.status === 'COMPLETED' && 'text-[var(--color-green)]',
          step.status === 'FAILED' && 'text-[var(--color-red)]',
          step.status === 'PENDING' && 'text-[var(--color-text-tertiary)]',
        )} />
      </div>
      <span className="text-[10px] text-[var(--color-text-secondary)] text-center leading-tight max-w-14">{step.name}</span>
    </motion.button>
  )
}
