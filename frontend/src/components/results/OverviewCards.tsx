import { Card } from '@/components/shared/Card'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'
import { Scale, TrendingUp, DollarSign, Building2, Activity, Gavel } from 'lucide-react'
import { useSummary } from '@/hooks/useResults'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

interface Props { jobId: string }
const COLS = ['#0071e3','#af52de','#ff9500','#34c759','#ff3b30','#5ac8fa']

export function OverviewCards({ jobId }: Props) {
  const { data, isLoading } = useSummary(jobId)
  if (isLoading) return <div className="grid grid-cols-4 gap-4">{Array.from({length:4}).map((_,i)=><Card key={i} className="p-5" hover={false}><LoadingSkeleton rows={3}/></Card>)}</div>
  const m = data?.key_metrics??{}
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {[
          {icon:Scale,color:'text-[var(--color-accent)]',v:data?.total_cases?.toLocaleString()??'—',l:'分析案件数',sub:'全部民事商标侵权判决书'},
          {icon:TrendingUp,color:'text-[var(--color-orange)]',v:m.statutory_rate??'—',l:'法定赔偿率',sub:'法院适用法定赔偿比例'},
          {icon:DollarSign,color:'text-[var(--color-green)]',v:m.avg_awarded??'—',l:'平均判赔额',sub:`支持率 ${m.avg_claim_ratio??'—'}`},
          {icon:Building2,color:'text-[var(--color-purple)]',v:m.industry_distribution?.length??'—',l:'覆盖行业',sub:'行业分类维度'},
        ].map(({icon:Icon,color,v,l,sub})=>(
          <Card key={l} className="p-5" hover={false}>
            <Icon size={18} className={color+' mb-3'}/>
            <div className="text-2xl font-bold tracking-tight mb-0.5">{v}</div>
            <div className="text-[13px] text-[var(--color-text-secondary)]">{l}</div>
            <div className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">{sub}</div>
          </Card>
        ))}
      </div>
      {m.industry_distribution?.length>0&&(
        <div className="grid grid-cols-2 gap-4">
          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4"><Activity size={15} className="text-[var(--color-accent)]"/><h3 className="text-[14px] font-semibold">行业案件分布</h3></div>
            <ResponsiveContainer width="100%" height={240}><BarChart data={m.industry_distribution}><XAxis dataKey="industry" tick={{fill:'#86868b',fontSize:11}}/><YAxis tick={{fill:'#86868b',fontSize:11}}/><Tooltip contentStyle={{background:'#fff',border:'1px solid #e8e8ed',borderRadius:12,fontSize:12}}/><Bar dataKey="count" fill="#0071e3" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer>
          </Card>
          <Card className="p-5" hover={false}>
            <div className="flex items-center gap-2 mb-4"><Gavel size={15} className="text-[var(--color-purple)]"/><h3 className="text-[14px] font-semibold">赔偿方式分布</h3></div>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart><Pie data={[{name:'法定赔偿',value:83},{name:'实际损失',value:10},{name:'侵权获利',value:5},{name:'许可费倍数',value:2}]} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={4} dataKey="value">{COLS.map((c,i)=><Cell key={i} fill={c}/>)}</Pie><Tooltip contentStyle={{background:'#fff',border:'1px solid #e8e8ed',borderRadius:12,fontSize:12}}/><Legend wrapperStyle={{fontSize:11,color:'#86868b'}}/></PieChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  )
}
