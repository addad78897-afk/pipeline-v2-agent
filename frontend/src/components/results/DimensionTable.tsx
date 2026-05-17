import { Card } from '@/components/shared/Card'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'

interface DimensionTableProps { jobId: string }

// Mock columns for 19 dimensions
const COLUMNS = [
  '案件ID', '原告诉请金额', '判赔金额', '法定赔偿率', '侵权认定', '赔偿方式',
  '行业分类', '法院层级', '审理程序', '证据类型', '说理深度', '利润率采纳',
  '主观恶意', '商标近似度', '混淆可能性', '侵权持续时间', '合理费用支持',
  '判赔率', '裁判要点',
]

const MOCK_ROWS = Array.from({ length: 10 }).map((_, i) => ({
  id: `case-${i + 1}`,
  values: [
    `(2024)粤01${String(i + 1).padStart(2, '0')}民初${100 + i}号`,
    `¥${(5 + Math.random() * 50).toFixed(0)},000`,
    `¥${(1 + Math.random() * 10).toFixed(0)},000`,
    `${(20 + Math.random() * 60).toFixed(1)}%`,
    Math.random() > 0.5 ? '成立' : '部分成立',
    Math.random() > 0.5 ? '法定赔偿' : '实际损失',
    ['服装', '电子产品', '食品', '日化'][Math.floor(Math.random() * 4)],
    ['中级法院', '基层法院', '知识产权法院'][Math.floor(Math.random() * 3)],
    Math.random() > 0.3 ? '一审' : '二审',
    '商标注册证、销售记录',
    `${(1 + Math.random() * 5).toFixed(1)}/5`,
    Math.random() > 0.5 ? 'A1_完全采信' : 'B1_部分采信',
    Math.random() > 0.5 ? '明显恶意' : '一般过失',
    `${(50 + Math.random() * 50).toFixed(0)}%`,
    Math.random() > 0.5 ? '高' : '中',
    `${(1 + Math.random() * 3).toFixed(0)}年`,
    Math.random() > 0.5 ? '支持' : '部分支持',
    `${(10 + Math.random() * 50).toFixed(1)}%`,
    ['停止侵权', '赔偿损失', '消除影响'][Math.floor(Math.random() * 3)],
  ],
}))

export function DimensionTable({ jobId: _ }: DimensionTableProps) {
  return (
    <Card className="overflow-hidden" hover={false}>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              {COLUMNS.map((col) => (
                <th key={col} className="text-left px-3 py-2.5 text-[var(--color-text-muted)] font-medium whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_ROWS.map((row) => (
              <tr key={row.id} className="border-b border-[var(--color-border)]/50 hover:bg-white/5 transition-colors">
                {row.values.map((v, i) => (
                  <td key={i} className="px-3 py-2 text-[var(--color-text-secondary)] whitespace-nowrap">{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border)]">
        <span className="text-xs text-[var(--color-text-muted)]">共 10,435 条 · 当前显示前10条</span>
        <div className="flex gap-1">
          <button className="px-3 py-1 text-xs rounded bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10">上一页</button>
          <button className="px-3 py-1 text-xs rounded bg-cyan-500/10 text-cyan-400">1</button>
          <button className="px-3 py-1 text-xs rounded bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10">2</button>
          <button className="px-3 py-1 text-xs rounded bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10">下一页</button>
        </div>
      </div>
    </Card>
  )
}
