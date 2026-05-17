import { useParams } from 'react-router-dom'
import { OverviewCards } from '@/components/results/OverviewCards'
import { DimensionTable } from '@/components/results/DimensionTable'
import { ChartGallery } from '@/components/results/ChartGallery'
import { ReportViewer } from '@/components/results/ReportViewer'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'
import { usePipelineStore } from '@/store/pipelineStore'
import { BarChart3, FileText, Grid3X3, Image } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/utils/cn'

const TABS = [
  { id: 'overview', label: '概览', icon: BarChart3 },
  { id: 'dimensions', label: '19维分析', icon: Grid3X3 },
  { id: 'charts', label: '图表', icon: Image },
  { id: 'reports', label: '报告', icon: FileText },
]

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { jobStatus } = usePipelineStore()
  const [activeTab, setActiveTab] = useState('overview')

  if (jobStatus === 'RUNNING' || jobStatus === 'QUEUED') {
    return (
      <div className="max-w-6xl mx-auto py-24 px-6 text-center">
        <LoadingSkeleton rows={4} className="max-w-md mx-auto" />
        <p className="text-sm text-[var(--color-text-secondary)] mt-4">管线正在执行中，完成后自动加载结果...</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-6 space-y-6 animate-fade-in-up">
      <div className="flex items-center gap-2">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors',
              activeTab === id
                ? 'bg-white/10 text-[var(--color-text-primary)]'
                : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && <OverviewCards jobId={jobId!} />}
      {activeTab === 'dimensions' && <DimensionTable jobId={jobId!} />}
      {activeTab === 'charts' && <ChartGallery jobId={jobId!} />}
      {activeTab === 'reports' && <ReportViewer jobId={jobId!} />}
    </div>
  )
}
