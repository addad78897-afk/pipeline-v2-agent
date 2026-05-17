import { Card } from '@/components/shared/Card'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'
import { TrendingUp, Scale, Building2, DollarSign, Activity, Gavel } from 'lucide-react'
import { useSummary } from '@/hooks/useResults'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

interface OverviewCardsProps { jobId: string }

const COLORS = ['#00d4ff', '#e040fb', '#ffab00', '#00e676', '#ff5252', '#448aff']

export function OverviewCards({ jobId }: OverviewCardsProps) {
  const { data, isLoading } = useSummary(jobId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="p-5" hover={false}>
            <LoadingSkeleton rows={3} />
          </Card>
        ))}
      </div>
    )
  }

  const metrics = data?.key_metrics ?? {}

  return (
    <div className="space-y-6">
      {/* 关键指标卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3">
            <Scale size={20} className="text-cyan-400" />
          </div>
          <div className="text-2xl font-semibold mb-1">{data?.total_cases?.toLocaleString() ?? '—'}</div>
          <div className="text-sm text-[var(--color-text-secondary)]">分析案件数</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">全部民事商标侵权判决书</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3">
            <TrendingUp size={20} className="text-amber-400" />
          </div>
          <div className="text-2xl font-semibold mb-1">{metrics.statutory_rate ?? '—'}</div>
          <div className="text-sm text-[var(--color-text-secondary)]">法定赔偿率</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">法院适用法定赔偿比例</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3">
            <DollarSign size={20} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-semibold mb-1">{metrics.avg_awarded ?? '—'}</div>
          <div className="text-sm text-[var(--color-text-secondary)]">平均判赔额</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">原告诉请金额平均支持率 {metrics.avg_claim_ratio ?? '—'}</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3">
            <Building2 size={20} className="text-fuchsia-400" />
          </div>
          <div className="text-2xl font-semibold mb-1">{metrics.industry_distribution?.length ?? '—'}</div>
          <div className="text-sm text-[var(--color-text-secondary)]">覆盖行业</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">行业分类维度</div>
        </Card>
      </div>

      {/* 行业分布图 */}
      {metrics.industry_distribution && metrics.industry_distribution.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4">
              <Activity size={16} className="text-cyan-400" />
              <h3 className="text-sm font-medium">行业案件分布</h3>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={metrics.industry_distribution}>
                <XAxis dataKey="industry" tick={{ fill: '#606078', fontSize: 11 }} />
                <YAxis tick={{ fill: '#606078', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#141418', border: '1px solid #2a2a3a', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#e8e8ed' }}
                />
                <Bar dataKey="count" fill="#00d4ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4">
              <Gavel size={16} className="text-fuchsia-400" />
              <h3 className="text-sm font-medium">赔偿方式分布</h3>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={[
                    { name: '法定赔偿', value: 83 },
                    { name: '实际损失', value: 10 },
                    { name: '侵权获利', value: 5 },
                    { name: '许可费合理倍数', value: 2 },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {COLORS.map((color, i) => (
                    <Cell key={i} fill={color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#141418', border: '1px solid #2a2a3a', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#9898a8' }} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  )
}
