import { cn } from '@/utils/cn'
import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  onClick?: () => void
}

export function Card({ children, className, hover = true, onClick }: CardProps) {
  return (
    <div
      className={cn('glass', hover && 'hover:border-[var(--color-border-accent)] hover:bg-[var(--color-bg-card-hover)] transition-colors duration-200', onClick && 'cursor-pointer', className)}
      onClick={onClick}
    >
      {children}
    </div>
  )
}
