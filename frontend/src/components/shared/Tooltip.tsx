import { type ReactNode, useState } from 'react'
import { cn } from '@/utils/cn'

interface TooltipProps {
  content: string
  children: ReactNode
  side?: 'top' | 'bottom'
}

export function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  const [show, setShow] = useState(false)

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div
          className={cn(
            'absolute z-50 px-3 py-2 rounded-lg text-xs max-w-56',
            'bg-[#1a1a28] border border-[var(--color-border-accent)] text-[var(--color-text-secondary)]',
            'shadow-xl backdrop-blur-sm',
            side === 'top' && 'bottom-full mb-2 left-1/2 -translate-x-1/2',
            side === 'bottom' && 'top-full mt-2 left-1/2 -translate-x-1/2'
          )}
        >
          {content}
        </div>
      )}
    </div>
  )
}
