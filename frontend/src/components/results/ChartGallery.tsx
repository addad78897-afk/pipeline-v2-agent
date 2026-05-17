import { Card } from '@/components/shared/Card'
import { EmptyState } from '@/components/shared/LoadingSkeleton'
import { Image } from 'lucide-react'
import { useState } from 'react'

interface ChartGalleryProps { jobId: string }

const MOCK_CHARTS = [
  { name: '年度案件量与判赔额', desc: '2024-2026年度趋势' },
  { name: '法院层级赔偿方式', desc: '各级法院赔偿方式分布' },
  { name: '行业判赔差异', desc: '不同行业判赔金额对比' },
  { name: '法定赔偿率时间趋势', desc: '法定赔偿率月度变化' },
  { name: '利润率与判赔关联', desc: '利润率采纳与判赔金额关系' },
  { name: '详率分析', desc: '各子类型详情分析' },
]

export function ChartGallery({ jobId: _ }: ChartGalleryProps) {
  const [zoomed, setZoomed] = useState<string | null>(null)

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
      {MOCK_CHARTS.map((chart) => (
        <Card key={chart.name} className="p-4 cursor-pointer group" onClick={() => setZoomed(chart.name)}>
          <div className="aspect-video rounded-lg bg-white/5 flex items-center justify-center mb-3 group-hover:bg-white/10 transition-colors">
            <div className="text-center">
              <Image size={24} className="mx-auto mb-1 text-[var(--color-text-muted)]" />
              <span className="text-[10px] text-[var(--color-text-muted)]">点击放大</span>
            </div>
          </div>
          <div className="text-sm font-medium">{chart.name}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{chart.desc}</div>
        </Card>
      ))}
    </div>
  )
}
