import { Card } from '@/components/shared/Card'
import { Image } from 'lucide-react'
import { useState } from 'react'

interface Props { jobId: string }

const CHARTS = [
  { name: '年度案件量与判赔额', desc: '2024-2026年度趋势' },
  { name: '法院层级赔偿方式', desc: '各级法院赔偿方式分布' },
  { name: '行业判赔差异', desc: '不同行业判赔金额对比' },
  { name: '法定赔偿率时间趋势', desc: '法定赔偿率月度变化' },
  { name: '利润率与判赔关联', desc: '利润率采纳与判赔金额关系' },
  { name: '详情分析', desc: '各子类型详情分析' },
]

export function ChartGallery({ jobId: _ }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {CHARTS.map(c=>(
        <Card key={c.name} className="p-4 cursor-pointer">
          <div className="aspect-video rounded-xl bg-[var(--color-bg-primary)] flex items-center justify-center mb-3 border border-[var(--color-border-light)]">
            <div className="text-center"><Image size={22} className="mx-auto mb-1 text-[var(--color-text-tertiary)]"/><span className="text-[10px] text-[var(--color-text-tertiary)]">点击放大</span></div>
          </div>
          <div className="text-[13px] font-semibold">{c.name}</div>
          <div className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">{c.desc}</div>
        </Card>
      ))}
    </div>
  )
}
