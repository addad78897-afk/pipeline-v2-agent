import { motion } from 'framer-motion'
import { Check, X, Clock, RefreshCw } from 'lucide-react'
import { cn } from '@/utils/cn'

interface Props { toolId:string; toolName:string; phase:number; status:'running'|'success'|'error'|'retrying'; durationSeconds?:number; outputSummary?:string; error?:string; isLatest:boolean }

const pc: Record<number,{bg:string;border:string;labelBg:string;labelText:string}> = {
  1:{bg:'bg-[var(--color-teal)]/4',border:'border-[var(--color-teal)]/20',labelBg:'bg-[var(--color-teal)]/12',labelText:'text-[var(--color-teal)]'},
  2:{bg:'bg-[var(--color-purple)]/4',border:'border-[var(--color-purple)]/20',labelBg:'bg-[var(--color-purple)]/12',labelText:'text-[var(--color-purple)]'},
  3:{bg:'bg-[var(--color-orange)]/4',border:'border-[var(--color-orange)]/20',labelBg:'bg-[var(--color-orange)]/12',labelText:'text-[var(--color-orange)]'},
}

const ss: Record<string,{bg:string;border:string}> = {
  running:{bg:'bg-[var(--color-orange)]/4',border:'border-[var(--color-orange)]/20'},
  success:{bg:'bg-[var(--color-green)]/6',border:'border-[var(--color-green)]/20'},
  error:{bg:'bg-[var(--color-red)]/6',border:'border-[var(--color-red)]/20'},
  retrying:{bg:'bg-[var(--color-purple)]/4',border:'border-[var(--color-purple)]/20'},
}

export function ToolCallCard({ toolId, toolName, phase, status, durationSeconds, outputSummary, error, isLatest }: Props) {
  const p = pc[phase]??pc[1]; const s = ss[status]??ss.running
  return (
    <motion.div initial={isLatest?{opacity:0,scale:.95}:false} animate={{opacity:1,scale:1}} className={cn('flex items-start gap-3 px-4 py-3 rounded-xl border',s.bg,s.border)}>
      <div className="shrink-0 mt-0.5">
        {status==='running'&&<Clock size={13} className="text-[var(--color-orange)] animate-pulse"/>}
        {status==='retrying'&&<RefreshCw size={13} className="text-[var(--color-purple)] animate-spin"/>}
        {status==='success'&&<Check size={13} className="text-[var(--color-green)]"/>}
        {status==='error'&&<X size={13} className="text-[var(--color-red)]"/>}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={cn('text-[10px] px-1.5 py-0.5 rounded-md font-semibold',p.labelBg,p.labelText)}>阶段{phase}</span>
          <span className="text-[12px] font-semibold">{toolName}</span>
          {durationSeconds!=null&&<span className="text-[10px] text-[var(--color-text-tertiary)] ml-auto">{durationSeconds}s</span>}
        </div>
        {outputSummary&&status==='success'&&<div className="mt-1 p-2 rounded-lg bg-white/60 text-[11px] text-[var(--color-text-tertiary)] font-mono line-clamp-2">{outputSummary}</div>}
        {error&&<div className="mt-1 text-[11px] text-[var(--color-red)]">{error}</div>}
      </div>
    </motion.div>
  )
}
