import { useParams, useNavigate } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Lightbulb, CheckCircle, Activity, TrendingUp, FileText, Shield } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAgentStore } from '@/store/agentStore'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'
import { AgentThoughtBubble } from '@/components/agent/AgentThoughtBubble'
import { ToolCallCard } from '@/components/agent/ToolCallCard'
import { DocumentDecisionPanel } from '@/components/agent/DocumentDecisionPanel'
import { Card } from '@/components/shared/Card'

const TABS = [
  { id: 'thoughts' as const, label: '思维流', icon: Brain },
  { id: 'decisions' as const, label: '决策', icon: FileText },
  { id: 'overview' as const, label: '概览', icon: Activity },
]

export function AgentPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const store = useAgentStore()
  const [tab, setTab] = useState<'thoughts'|'decisions'|'overview'>('thoughts')
  const [selectedDocIdx, setSelectedDocIdx] = useState<number|null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { if (jobId && !store.jobId) useAgentStore.setState({ jobId, jobStatus: 'QUEUED', fileCount: 0 }) }, [jobId])
  useAgentWebSocket(jobId ?? null)
  useEffect(() => { if (tab === 'thoughts') endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [store.thoughts.length, tab])
  useEffect(() => { if (store.jobStatus === 'COMPLETED' && jobId) { const t = setTimeout(() => navigate(`/results/${jobId}`), 3000); return () => clearTimeout(t) } }, [store.jobStatus, jobId])

  const selDoc = store.docCompletions.find(d => d.document_index === selectedDocIdx)
  const totalTools = store.toolEvents.length
  const ok = store.toolEvents.filter(e => 'verified' in e && e.verified).length
  const err = store.toolEvents.filter(e => 'error' in e).length
  const strats: Record<string,number> = {}
  store.docCompletions.forEach(d => { strats[d.strategy_used] = (strats[d.strategy_used]||0)+1 })

  const statusBg = store.jobStatus === 'RUNNING' ? 'bg-[var(--color-accent)]/4 border-[var(--color-accent)]/20' :
    store.jobStatus === 'COMPLETED' ? 'bg-[var(--color-green)]/6 border-[var(--color-green)]/20' :
    store.jobStatus === 'FAILED' ? 'bg-[var(--color-red)]/6 border-[var(--color-red)]/20' :
    'bg-[var(--color-bg-tertiary)] border-[var(--color-border-light)]'

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-auto p-6">
        {store.jobStatus && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className={cn('mb-6 p-4 rounded-2xl border', statusBg)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', store.jobStatus==='RUNNING'?'bg-[var(--color-accent)]/10':store.jobStatus==='COMPLETED'?'bg-[var(--color-green)]/10':'')}>
                  {store.jobStatus==='QUEUED' && <Activity size={18} className="text-[var(--color-text-tertiary)]" />}
                  {store.jobStatus==='RUNNING' && <Brain size={18} className="text-[var(--color-accent)] animate-pulse" />}
                  {store.jobStatus==='COMPLETED' && <CheckCircle size={18} className="text-[var(--color-green)]" />}
                </div>
                <div>
                  <div className="text-[14px] font-semibold">
                    {store.jobStatus==='QUEUED'&&'Agent 正在连接...'}
                    {store.jobStatus==='RUNNING'&&`正在自主分析 ${store.fileCount} 份判决书`}
                    {store.jobStatus==='COMPLETED'&&'分析完成，即将跳转结果页'}
                    {store.jobStatus==='FAILED'&&'分析失败'}
                  </div>
                  <div className="text-[12px] text-[var(--color-text-tertiary)] mt-0.5">
                    {store.jobStatus==='RUNNING'&&<>{store.documentsProcessed}/{store.fileCount} 份 · {totalTools} 次调用 · {ok}✓ {err>0?`${err}✗`:''}</>}
                    {store.agentComplete&&<>总计 {store.agentComplete.total_tools_run} 次调用 · 节省 {store.agentComplete.total_llm_calls_saved} 次LLM · {store.agentComplete.total_duration_seconds}s</>}
                  </div>
                </div>
              </div>
              <div className="flex gap-1 flex-wrap">{Object.entries(strats).map(([s,c])=>(
                <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/60 text-[var(--color-text-tertiary)]">{s==='standard'?'标准':s==='minimal'?'精简':s==='rule_only'?'纯规则':'快速'}:{c}</span>
              ))}</div>
            </div>
            {store.jobStatus==='RUNNING'&&store.fileCount>0&&(
              <div className="mt-3 h-1 rounded-full bg-black/[0.06] overflow-hidden">
                <motion.div className="h-full rounded-full bg-[var(--color-accent)]" animate={{width:`${(store.documentsProcessed/store.fileCount)*100}%`}} transition={{duration:0.3}}/>
              </div>
            )}
          </motion.div>
        )}

        <div className="flex items-center gap-1 mb-4 bg-[var(--color-bg-primary)] rounded-xl p-1 w-fit">
          {TABS.map(({id,label,icon:Icon})=>(
            <button key={id} onClick={()=>setTab(id)} className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all', tab===id?'bg-white text-[var(--color-text-primary)] shadow-sm':'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]')}>
              <Icon size={15}/>{label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {tab==='thoughts'&&(
            <motion.div key="t" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3 max-w-2xl">
              {store.thoughts.length===0&&(
                <div className="text-center py-16">
                  <Brain size={36} className="mx-auto mb-3 text-[var(--color-text-tertiary)] animate-pulse"/>
                  <p className="text-[14px] text-[var(--color-text-secondary)] font-medium">Agent 正在连接...</p>
                  <p className="text-[12px] text-[var(--color-text-tertiary)] mt-1">即将逐份感知文书，自主规划策略</p>
                </div>
              )}
              {store.thoughts.map((t,i)=>(<AgentThoughtBubble key={i} thought={t.thought} phase={t.phase} timestamp={t.timestamp} isLatest={i===store.thoughts.length-1&&store.jobStatus==='RUNNING'}/>))}
              <div ref={endRef}/>
            </motion.div>
          )}
          {tab==='decisions'&&(
            <motion.div key="d" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="grid grid-cols-[280px_1fr] gap-6">
              <DocumentDecisionPanel documents={store.docCompletions.map(d=>{const p=store.thoughts.find(t=>t.documentIndex===d.document_index&&t.phase==='plan');return{filename:d.filename,document_index:d.document_index,quality_score:d.quality_score,strategy:d.strategy_used,strategy_name:p?.plan?.strategy_name??d.strategy_used,anomalies:[],tools_selected:p?.plan?.selected_tool_ids??[],tools_run:d.tools_run,errors:d.errors}})} selectedDoc={selDoc?{...selDoc,filename:selDoc.filename,document_index:selDoc.document_index,quality_score:selDoc.quality_score,strategy:selDoc.strategy_used,strategy_name:selDoc.strategy_used,anomalies:[],tools_selected:[],tools_run:selDoc.tools_run,errors:selDoc.errors}:null} onSelect={d=>setSelectedDocIdx(d.document_index)} onClose={()=>setSelectedDocIdx(null)}/>
              <div>{selDoc?(
                <div className="space-y-2">
                  <div className="flex items-center gap-2 mb-3"><FileText size={14} className="text-[var(--color-text-tertiary)]"/><h3 className="text-[14px] font-semibold">{selDoc.filename}</h3></div>
                  <Card className="p-3" hover={false}><div className="flex items-center gap-2 mb-2"><Lightbulb size={14} className="text-[var(--color-purple)]"/><span className="text-[12px] font-semibold">Agent 决策</span></div><div className="text-[12px] text-[var(--color-text-tertiary)]">策略 {selDoc.strategy_used} · {selDoc.tools_run} 工具 · {selDoc.errors} 错误</div></Card>
                  {store.toolEvents.filter(e=>e.documentIndex===selDoc.document_index).map((e,i)=>{const isLast=i===store.toolEvents.filter(x=>x.documentIndex===selDoc.document_index).length-1;return 'verified' in e?<ToolCallCard key={i} toolId={e.tool_id} toolName={e.tool_name} phase={e.phase} status="success" durationSeconds={e.duration_seconds} outputSummary={e.output_summary} isLatest={isLast&&store.jobStatus==='RUNNING'}/>:<ToolCallCard key={i} toolId={e.tool_id} toolName={e.tool_name} phase={e.phase} status={e.will_retry?'retrying':'error'} error={e.error} isLatest={false}/>})}
                </div>
              ):(<div className="text-center py-16"><Shield size={28} className="mx-auto mb-3 text-[var(--color-text-tertiary)]"/><p className="text-[13px] text-[var(--color-text-secondary)]">选择左侧文书查看详情</p></div>)}</div>
            </motion.div>
          )}
          {tab==='overview'&&(
            <motion.div key="o" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-4 max-w-2xl">
              <Card className="p-5" hover={false}>
                <div className="flex items-center gap-2 mb-4"><Brain size={16} className="text-[var(--color-accent)]"/><h3 className="text-[14px] font-semibold">Agent 工作循环</h3></div>
                <div className="grid grid-cols-5 gap-3">
                  {[{p:'观察',c:'var(--color-teal)',d:'感知文书\n编码/结构/异常'},{p:'规划',c:'var(--color-purple)',d:'自主选择\n工具和策略'},{p:'执行',c:'var(--color-orange)',d:'调用工具\n记录结果'},{p:'核查',c:'var(--color-green)',d:'验证质量\n不通过重试'},{p:'记录',c:'var(--color-text-tertiary)',d:'写入记忆\n更新统计'}].map(({p,c,d})=>(
                    <div key={p} className="text-center"><div className="w-9 h-9 rounded-xl flex items-center justify-center mx-auto mb-1.5" style={{backgroundColor:`${c}18`}}><Activity size={15} style={{color:c}}/></div><div className="text-[12px] font-semibold">{p}</div><div className="text-[10px] text-[var(--color-text-tertiary)] mt-0.5 whitespace-pre-line">{d}</div></div>
                  ))}
                </div>
              </Card>
              <Card className="p-5" hover={false}>
                <div className="flex items-center gap-2 mb-4"><Shield size={16} className="text-[var(--color-purple)]"/><h3 className="text-[14px] font-semibold">自适应策略</h3></div>
                <div className="space-y-1.5">
                  {[{n:'标准流程',id:'standard',d:'结构完整·质量好 → 16步全走',c:'text-[var(--color-green)] bg-[var(--color-green)]/6 border-[var(--color-green)]/20'},{n:'精简流程',id:'minimal',d:'缺段落·质量一般 → 跳过LLM',c:'text-[var(--color-orange)] bg-[var(--color-orange)]/6 border-[var(--color-orange)]/20'},{n:'纯规则',id:'rule_only',d:'质量差 → 仅规则引擎',c:'text-[var(--color-text-tertiary)] bg-black/[0.04] border-[var(--color-border-light)]'},{n:'快速扫描',id:'quick_scan',d:'非民事 → 基础提取',c:'text-[var(--color-red)] bg-[var(--color-red)]/6 border-[var(--color-red)]/20'}].map(s=>{const n=strats[s.id];return(<div key={s.id} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--color-bg-tertiary)]"><span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full border',s.c)}>{s.n}</span><span className="flex-1 text-[12px] text-[var(--color-text-secondary)]">{s.d}</span>{n>0&&<span className="text-[12px] text-[var(--color-text-tertiary)]">{n}份</span>}</div>)})}
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
