import { Card } from '@/components/shared/Card'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'
import { TrendingUp, Scale, Building2, DollarSign, Activity, Gavel } from 'lucide-react'
import { useSummary } from '@/hooks/useResults'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

interface OverviewCardsProps { jobId: string }

const COLORS = ['#0891b2', '#a21caf', '#d97706', '#059669', '#dc2626', '#4f46e5']

export function OverviewCards({ jobId }: OverviewCardsProps) {
  const { data, isLoading } = useSummary(jobId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="p-5" hover={false}><LoadingSkeleton rows={3} /></Card>
        ))}
      </div>
    )
  }

  const metrics = data?.key_metrics ?? {}

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3"><Scale size={20} className="text-cyan-600" /></div>
          <div className="text-2xl font-bold text-gray-900 mb-1">{data?.total_cases?.toLocaleString() ?? '—'}</div>
          <div className="text-sm text-gray-500">分析案件数</div>
          <div className="text-xs text-gray-400 mt-1">全部民事商标侵权判决书</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3"><TrendingUp size={20} className="text-amber-600" /></div>
          <div className="text-2xl font-bold text-gray-900 mb-1">{metrics.statutory_rate ?? '—'}</div>
          <div className="text-sm text-gray-500">法定赔偿率</div>
          <div className="text-xs text-gray-400 mt-1">法院适用法定赔偿比例</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3"><DollarSign size={20} className="text-emerald-600" /></div>
          <div className="text-2xl font-bold text-gray-900 mb-1">{metrics.avg_awarded ?? '—'}</div>
          <div className="text-sm text-gray-500">平均判赔额</div>
          <div className="text-xs text-gray-400 mt-1">原告诉请金额平均支持率 {metrics.avg_claim_ratio ?? '—'}</div>
        </Card>

        <Card className="p-5" hover={false}>
          <div className="flex items-start justify-between mb-3"><Building2 size={20} className="text-purple-600" /></div>
          <div className="text-2xl font-bold text-gray-900 mb-1">{metrics.industry_distribution?.length ?? '—'}</div>
          <div className="text-sm text-gray-500">覆盖行业</div>
          <div className="text-xs text-gray-400 mt-1">行业分类维度</div>
        </Card>
      </div>

      {metrics.industry_distribution && metrics.industry_distribution.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4">
              <Activity size={16} className="text-cyan-600" />
              <h3 className="text-sm font-semibold text-gray-700">行业案件分布</h3>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={metrics.industry_distribution}>
                <XAxis dataKey="industry" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#111827' }} />
                <Bar dataKey="count" fill="#0891b2" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4">
              <Gavel size={16} className="text-purple-600" />
              <h3 className="text-sm font-semibold text-gray-700">赔偿方式分布</h3>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={[
                  { name: '法定赔偿', value: 83 }, { name: '实际损失', value: 10 },
                  { name: '侵权获利', value: 5 }, { name: '许可费合理倍数', value: 2 },
                ]} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={4} dataKey="value">
                  {COLORS.map((color, i) => (<Cell key={i} fill={color} />))}
                </Pie>
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  )
}
