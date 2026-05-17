import { NavLink } from 'react-router-dom'
import { Upload, Play, BarChart3, Clock, Brain } from 'lucide-react'
import { cn } from '@/utils/cn'

const navItems = [
  { to: '/', icon: Upload, label: '上传文书' },
  { to: '/history', icon: Clock, label: '历史记录' },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-[var(--color-border)] bg-white flex flex-col shadow-[1px_0_4px_rgba(0,0,0,0.03)]">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center shadow-sm">
            <span className="text-xs font-bold text-white">V2</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">管线V2.0</div>
            <div className="text-[10px] text-gray-400">商标侵权裁判文书分析</div>
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
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-100 text-gray-900'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
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
        <div className="text-[10px] text-gray-400">
          基于 DeepSeek-chat · 豆包
        </div>
        <div className="mt-1 flex items-center gap-1">
          <Brain size={10} className="text-purple-400" />
          <span className="text-[10px] text-purple-500 font-medium">Agent 模式</span>
        </div>
      </div>
    </aside>
  )
}
