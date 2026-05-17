import { useLocation } from 'react-router-dom'
import { Badge } from '@/components/shared/Badge'
import { usePipelineStore } from '@/store/pipelineStore'
import { useAgentStore } from '@/store/agentStore'

const TITLES: Record<string, string> = {
  '/': '上传判决文书',
  '/history': '历史记录',
}

export function TopBar() {
  const location = useLocation()
  const { jobStatus, currentStep } = usePipelineStore()
  const agentStatus = useAgentStore((s) => s.jobStatus)
  const documentsProcessed = useAgentStore((s) => s.documentsProcessed)
  const fileCount = useAgentStore((s) => s.fileCount)

  const isPipeline = location.pathname.startsWith('/pipeline/')
  const isAgent = location.pathname.startsWith('/agent/')
  const isResults = location.pathname.startsWith('/results/')

  let title = TITLES[location.pathname] ?? ''
  if (isPipeline) title = '管线运行中'
  if (isAgent) title = 'Agent 自主分析中'
  if (isResults) title = '分析结果'

  return (
    <header className="h-14 shrink-0 border-b border-[var(--color-border)] flex items-center justify-between px-6 bg-[var(--color-bg-primary)]/80 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-medium text-[var(--color-text-primary)]">{title}</h1>
        {isPipeline && jobStatus && (
          <Badge status={jobStatus} />
        )}
        {isAgent && (
          <span className="text-[11px] px-2 py-0.5 rounded bg-gradient-to-r from-cyan-500/10 to-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-400/20 font-medium">
            Agent {agentStatus === 'RUNNING' ? '运行中' : agentStatus === 'COMPLETED' ? '完成' : ''}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {isPipeline && currentStep > 0 && (
          <span className="text-xs text-[var(--color-text-muted)]">
            Step {currentStep}/16
          </span>
        )}
        {isAgent && documentsProcessed > 0 && (
          <span className="text-xs text-[var(--color-text-muted)]">
            {documentsProcessed}/{fileCount} 份
          </span>
        )}
      </div>
    </header>
  )
}
