import { Card } from '@/components/shared/Card'
import { FileText } from 'lucide-react'

interface Props { jobId: string }

const REPORTS = [
  { name: '统计结论', desc: '7项假设检验的统计推断结果' },
  { name: '三阶梯证据标准', desc: '证据标准三阶梯分类模型' },
  { name: '同案不同判分析', desc: '相似案情下的裁判冲突检测' },
  { name: '计量经济学建模', desc: '4个计量经济模型结果' },
  { name: '时间趋势分析', desc: '时间序列分析报告' },
]

export function ReportViewer({ jobId: _ }: Props) {
  return (
    <div className="space-y-2">
      {REPORTS.map(r=>(
        <Card key={r.name} className="p-4 flex items-center gap-4">
          <div className="w-9 h-9 rounded-xl bg-[var(--color-accent)]/8 flex items-center justify-center shrink-0"><FileText size={18} className="text-[var(--color-accent)]"/></div>
          <div className="flex-1 min-w-0"><div className="text-[14px] font-semibold">{r.name}</div><div className="text-[12px] text-[var(--color-text-tertiary)] mt-0.5">{r.desc}</div></div>
          <button className="text-[12px] px-4 py-1.5 rounded-full bg-[var(--color-accent)] text-white font-semibold hover:bg-[var(--color-accent-hover)] transition-colors">查看</button>
        </Card>
      ))}
    </div>
  )
}
