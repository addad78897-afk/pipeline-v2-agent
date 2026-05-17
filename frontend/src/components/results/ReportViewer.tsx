import { Card } from '@/components/shared/Card'
import { FileText } from 'lucide-react'

interface ReportViewerProps { jobId: string }

const REPORTS = [
  { name: '统计结论', desc: '7项假设检验的统计推断结果', source: '统计结论_7项假设检验.txt' },
  { name: '三阶梯证据标准', desc: '证据标准三阶梯分类模型', source: '三阶梯_证据标准模型报告.md' },
  { name: '同案不同判分析', desc: '相似案情下的裁判冲突检测', source: '同案不同判_冲突分析报告.md' },
  { name: '计量经济学建模', desc: '4个计量经济模型结果', source: '计量经济学_建模结果.md' },
  { name: '时间趋势分析', desc: '时间序列分析报告', source: '时间趋势_分析报告.md' },
]

export function ReportViewer({ jobId: _ }: ReportViewerProps) {
  return (
    <div className="space-y-3">
      {REPORTS.map((report) => (
        <Card key={report.name} className="p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-cyan-50 flex items-center justify-center shrink-0 border border-cyan-100">
            <FileText size={20} className="text-cyan-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-gray-700">{report.name}</div>
            <div className="text-xs text-gray-400 mt-0.5">{report.desc}</div>
          </div>
          <button className="text-xs px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-800 font-medium transition-colors">
            查看
          </button>
        </Card>
      ))}
    </div>
  )
}
