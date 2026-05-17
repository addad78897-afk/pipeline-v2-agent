import { NavLink } from 'react-router-dom'
import { Upload, Play, BarChart3, Clock } from 'lucide-react'
import { cn } from '@/utils/cn'

const navItems = [
  { to: '/', icon: Upload, label: '上传文书' },
  { to: '/history', icon: Clock, label: '历史记录' },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)] flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-magenta-400 flex items-center justify-center">
            <span className="text-xs font-bold text-black">V2</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)]">管线V2.0</div>
            <div className="text-[10px] text-[var(--color-text-muted)]">商标侵权裁判文书分析</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-white/10 text-[var(--color-text-primary)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[var(--color-border)]">
        <div className="text-[10px] text-[var(--color-text-muted)]">
          基于 DeepSeek-chat · 豆包
        </div>
      </div>
    </aside>
  )
}
