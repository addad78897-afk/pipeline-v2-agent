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
  { id: 'dimensions', label: '19维', icon: Grid3X3 },
  { id: 'charts', label: '图表', icon: Image },
  { id: 'reports', label: '报告', icon: FileText },
]

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { jobStatus } = usePipelineStore()
  const [activeTab, setActiveTab] = useState('overview')

  if (jobStatus === 'RUNNING' || jobStatus === 'QUEUED') {
    return (
      <div className="max-w-4xl mx-auto py-24 px-6 text-center">
        <LoadingSkeleton rows={4} className="max-w-md mx-auto" />
        <p className="text-[14px] text-[var(--color-text-tertiary)] mt-4">管线正在执行中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-6 space-y-6 animate-fade-up">
      <div className="flex items-center gap-1 bg-[var(--color-bg-primary)] rounded-xl p-1 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)} className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all', activeTab===id?'bg-white text-[var(--color-text-primary)] shadow-sm':'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]')}>
            <Icon size={15} />{label}
          </button>
        ))}
      </div>
      {activeTab==='overview'&&<OverviewCards jobId={jobId!}/>}
      {activeTab==='dimensions'&&<DimensionTable jobId={jobId!}/>}
      {activeTab==='charts'&&<ChartGallery jobId={jobId!}/>}
      {activeTab==='reports'&&<ReportViewer jobId={jobId!}/>}
    </div>
  )
}
