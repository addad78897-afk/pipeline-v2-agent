import { Card } from '@/components/shared/Card'
import { Badge } from '@/components/shared/Badge'
import { EmptyState } from '@/components/shared/LoadingSkeleton'
import { Clock, Trash2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useNavigate } from 'react-router-dom'

const MOCK = [
  { jobId: 'demo-001', status: 'COMPLETED' as const, fileCount: 50, createdAt: '2026-05-17', duration: '12m 34s' },
  { jobId: 'demo-002', status: 'COMPLETED' as const, fileCount: 3, createdAt: '2026-05-17', duration: '2m 08s' },
  { jobId: 'demo-003', status: 'FAILED' as const, fileCount: 100, createdAt: '2026-05-16', duration: '—' },
]

export function HistoryPage() {
  const navigate = useNavigate()
  return (
    <div className="max-w-xl mx-auto py-12 px-6 space-y-3 animate-fade-up">
      <div className="mb-6">
        <h2 className="text-[28px] font-bold tracking-tight mb-1">历史记录</h2>
        <p className="text-[14px] text-[var(--color-text-secondary)]">查看过往分析作业</p>
      </div>
      {MOCK.length===0?<EmptyState icon="📋" title="暂无记录" description="上传判决书运行分析后出现"/>:
        MOCK.map(j=>(
          <Card key={j.jobId} className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-9 h-9 rounded-xl bg-[var(--color-bg-primary)] flex items-center justify-center"><Clock size={18} className="text-[var(--color-text-tertiary)]"/></div>
              <div><div className="text-[14px] font-semibold">{j.fileCount} 份判决书</div><div className="text-[12px] text-[var(--color-text-tertiary)] mt-0.5">{j.createdAt} · {j.duration}</div></div>
            </div>
            <div className="flex items-center gap-3">
              <Badge status={j.status}/>
              <button onClick={()=>navigate(`/results/${j.jobId}`)} disabled={j.status!=='COMPLETED'} className={cn('text-[12px] px-3 py-1.5 rounded-full font-semibold transition-all',j.status==='COMPLETED'?'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]':'bg-black/[0.04] text-[var(--color-text-tertiary)] cursor-not-allowed')}>查看</button>
              <button className="p-1.5 rounded-lg text-[var(--color-text-tertiary)] hover:text-[var(--color-red)] hover:bg-[var(--color-red)]/6 transition-colors"><Trash2 size={14}/></button>
            </div>
          </Card>
        ))
      }
    </div>
  )
}
