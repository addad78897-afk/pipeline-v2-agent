import { NavLink } from 'react-router-dom'
import { Upload, Clock } from 'lucide-react'
import { cn } from '@/utils/cn'

const navItems = [
  { to: '/', icon: Upload, label: '上传文书' },
  { to: '/history', icon: Clock, label: '历史记录' },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-white/60 backdrop-blur-xl border-r border-[var(--color-border-light)] flex flex-col">
      <div className="px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)] flex items-center justify-center">
            <span className="text-xs font-bold text-white tracking-tight">V2</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)] tracking-tight">管线V2.0</div>
            <div className="text-[11px] text-[var(--color-text-tertiary)]">裁判文书分析系统</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors',
                isActive
                  ? 'bg-[var(--color-accent)]/8 text-[var(--color-accent)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-black/[0.04]'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-[var(--color-border-light)]">
        <div className="text-[11px] text-[var(--color-text-tertiary)]">
          DeepSeek-chat · Agent
        </div>
      </div>
    </aside>
  )
}
