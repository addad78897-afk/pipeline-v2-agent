import { useLocation } from 'react-router-dom'
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
  const docs = useAgentStore((s) => s.documentsProcessed)
  const total = useAgentStore((s) => s.fileCount)

  const isPipeline = location.pathname.startsWith('/pipeline/')
  const isAgent = location.pathname.startsWith('/agent/')
  const isResults = location.pathname.startsWith('/results/')

  let title = TITLES[location.pathname] ?? ''
  if (isPipeline) title = '管线运行中'
  if (isAgent) title = 'Agent 自主分析'
  if (isResults) title = '分析结果'

  return (
    <header className="apple-glass h-12 shrink-0 flex items-center justify-between px-6 z-10">
      <h1 className="text-[13px] font-semibold text-[var(--color-text-primary)] tracking-tight">{title}</h1>
      <div className="flex items-center gap-3">
        {isPipeline && jobStatus && (
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-[var(--color-accent)]/8 text-[var(--color-accent)] font-medium">
            {jobStatus === 'RUNNING' ? `Step ${currentStep}/16` : jobStatus === 'COMPLETED' ? '完成' : jobStatus}
          </span>
        )}
        {isAgent && (
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-[var(--color-purple)]/10 text-[var(--color-purple)] font-medium">
            {agentStatus === 'RUNNING' ? `${docs}/${total} 份` : agentStatus === 'COMPLETED' ? '完成' : agentStatus}
          </span>
        )}
      </div>
    </header>
  )
}
