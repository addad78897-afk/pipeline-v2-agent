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
            'bg-gray-900 border border-gray-700 text-gray-100',
            'shadow-lg',
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
