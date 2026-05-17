import { Card } from '@/components/shared/Card'

interface Props { jobId: string }

const COLS = ['案件ID','原告诉请金额','判赔金额','法定赔偿率','侵权认定','赔偿方式','行业分类','法院层级','审理程序','证据类型','说理深度','利润率采纳','主观恶意','商标近似度','混淆可能性','侵权持续时间','合理费用支持','判赔率','裁判要点']

const ROWS = Array.from({length:10}).map((_,i)=>({
  id:`case-${i+1}`,
  values:[`(2024)粤01${String(i+1).padStart(2,'0')}民初${100+i}号`,`¥${(5+Math.random()*50).toFixed(0)},000`,`¥${(1+Math.random()*10).toFixed(0)},000`,`${(20+Math.random()*60).toFixed(1)}%`,Math.random()>.5?'成立':'部分成立',Math.random()>.5?'法定赔偿':'实际损失',['服装','电子产品','食品','日化'][Math.floor(Math.random()*4)],['中级','基层','知产法院'][Math.floor(Math.random()*3)],Math.random()>.3?'一审':'二审','商标注册证、销售记录',`${(1+Math.random()*5).toFixed(1)}/5`,Math.random()>.5?'A1_完全采信':'B1_部分采信',Math.random()>.5?'明显恶意':'一般过失',`${(50+Math.random()*50).toFixed(0)}%`,Math.random()>.5?'高':'中',`${(1+Math.random()*3).toFixed(0)}年`,Math.random()>.5?'支持':'部分支持',`${(10+Math.random()*50).toFixed(1)}%`,['停止侵权','赔偿损失','消除影响'][Math.floor(Math.random()*3)]],
}))

export function DimensionTable({ jobId: _ }: Props) {
  return (
    <Card className="overflow-hidden" hover={false}>
      <div className="overflow-auto">
        <table className="w-full text-[12px]">
          <thead><tr className="border-b border-[var(--color-border-light)] bg-[var(--color-bg-tertiary)]">{COLS.map(c=><th key={c} className="text-left px-3 py-2.5 text-[var(--color-text-tertiary)] font-medium whitespace-nowrap">{c}</th>)}</tr></thead>
          <tbody>{ROWS.map(r=><tr key={r.id} className="border-b border-[var(--color-border-light)] hover:bg-[var(--color-bg-primary)] transition-colors">{r.values.map((v,i)=><td key={i} className="px-3 py-2 text-[var(--color-text-secondary)] whitespace-nowrap">{v}</td>)}</tr>)}</tbody>
        </table>
      </div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border-light)]">
        <span className="text-[12px] text-[var(--color-text-tertiary)]">共 10,435 条 · 显示前10条</span>
        <div className="flex gap-1">
          <button className="px-3 py-1 text-[12px] rounded-lg bg-white text-[var(--color-text-tertiary)] border border-[var(--color-border-light)] hover:bg-[var(--color-bg-primary)]">上页</button>
          <button className="px-3 py-1 text-[12px] rounded-lg bg-[var(--color-accent)] text-white font-medium">1</button>
          <button className="px-3 py-1 text-[12px] rounded-lg bg-white text-[var(--color-text-tertiary)] border border-[var(--color-border-light)] hover:bg-[var(--color-bg-primary)]">2</button>
          <button className="px-3 py-1 text-[12px] rounded-lg bg-white text-[var(--color-text-tertiary)] border border-[var(--color-border-light)] hover:bg-[var(--color-bg-primary)]">下页</button>
        </div>
      </div>
    </Card>
  )
}
