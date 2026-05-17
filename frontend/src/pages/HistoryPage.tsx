import { Card } from '@/components/shared/Card'
import { Badge } from '@/components/shared/Badge'
import { EmptyState } from '@/components/shared/LoadingSkeleton'
import { Clock, Trash2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useNavigate } from 'react-router-dom'

const MOCK_HISTORY = [
  { jobId: 'demo-001', status: 'COMPLETED' as const, fileCount: 50, createdAt: '2026-05-17 14:30', duration: '12分34秒' },
  { jobId: 'demo-002', status: 'COMPLETED' as const, fileCount: 3, createdAt: '2026-05-17 10:15', duration: '2分08秒' },
  { jobId: 'demo-003', status: 'FAILED' as const, fileCount: 100, createdAt: '2026-05-16 09:00', duration: '—' },
]

export function HistoryPage() {
  const navigate = useNavigate()

  return (
    <div className="max-w-3xl mx-auto py-12 px-6 space-y-4 animate-fade-in-up">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-1">历史记录</h2>
        <p className="text-sm text-gray-500">查看过往的分析作业及其结果</p>
      </div>

      {MOCK_HISTORY.length === 0 ? (
        <EmptyState icon="📋" title="暂无历史记录" description="上传判决书并运行分析后，作业会出现在这里" />
      ) : (
        MOCK_HISTORY.map((job) => (
          <Card key={job.jobId} className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                <Clock size={20} className="text-gray-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-700">{job.fileCount} 份判决书</div>
                <div className="text-xs text-gray-400 mt-0.5">{job.createdAt} · {job.duration}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge status={job.status} />
              <button
                onClick={() => navigate(`/results/${job.jobId}`)}
                className={cn(
                  'text-xs px-3 py-1.5 rounded-lg font-medium transition-colors',
                  job.status === 'COMPLETED'
                    ? 'bg-gray-900 text-white hover:bg-gray-800'
                    : 'opacity-50 cursor-not-allowed bg-gray-100 text-gray-400'
                )}
                disabled={job.status !== 'COMPLETED'}
              >
                查看结果
              </button>
              <button className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                <Trash2 size={14} />
              </button>
            </div>
          </Card>
        ))
      )}
    </div>
  )
}
