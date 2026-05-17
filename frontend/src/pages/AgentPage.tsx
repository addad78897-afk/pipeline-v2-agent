import { useParams, useNavigate } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain, Eye, Lightbulb, CheckCircle, Play, Activity,
  TrendingUp, FileText, Shield, AlertTriangle,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAgentStore } from '@/store/agentStore'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'
import { AgentThoughtBubble } from '@/components/agent/AgentThoughtBubble'
import { ToolCallCard } from '@/components/agent/ToolCallCard'
import { DocumentDecisionPanel } from '@/components/agent/DocumentDecisionPanel'
import { Card } from '@/components/shared/Card'

type TabId = 'thoughts' | 'decisions' | 'overview'

const TABS: { id: TabId; label: string; icon: typeof Brain }[] = [
  { id: 'thoughts', label: 'Agent 思维流', icon: Brain },
  { id: 'decisions', label: '逐份决策', icon: FileText },
  { id: 'overview', label: '运行概览', icon: Activity },
]

export function AgentPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const store = useAgentStore()
  const [activeTab, setActiveTab] = useState<TabId>('thoughts')
  const [selectedDocIdx, setSelectedDocIdx] = useState<number | null>(null)
  const thoughtEndRef = useRef<HTMLDivElement>(null)

  useAgentWebSocket(jobId ?? null)

  useEffect(() => {
    if (activeTab === 'thoughts') thoughtEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [store.thoughts.length, activeTab])

  useEffect(() => {
    if (store.jobStatus === 'COMPLETED' && jobId) {
      const timer = setTimeout(() => navigate(`/results/${jobId}`), 3000)
      return () => clearTimeout(timer)
    }
  }, [store.jobStatus, jobId, navigate])

  const selectedDoc = store.docCompletions.find(d => d.document_index === selectedDocIdx)
  const totalTools = store.toolEvents.length
  const successfulTools = store.toolEvents.filter(e => 'verified' in e && e.verified).length
  const failedTools = store.toolEvents.filter(e => 'error' in e).length
  const strategyCounts: Record<string, number> = {}
  store.docCompletions.forEach(d => { strategyCounts[d.strategy_used] = (strategyCounts[d.strategy_used] || 0) + 1 })

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-auto p-6">
        {/* 状态栏 */}
        {store.jobStatus && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              'mb-6 p-4 rounded-xl border shadow-sm',
              store.jobStatus === 'QUEUED' && 'bg-gray-50 border-gray-200',
              store.jobStatus === 'RUNNING' && 'bg-cyan-50 border-cyan-200',
              store.jobStatus === 'COMPLETED' && 'bg-emerald-50 border-emerald-200',
              store.jobStatus === 'FAILED' && 'bg-red-50 border-red-200',
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  'w-10 h-10 rounded-xl flex items-center justify-center',
                  store.jobStatus === 'RUNNING' && 'bg-cyan-100',
                  store.jobStatus === 'COMPLETED' && 'bg-emerald-100',
                )}>
                  {store.jobStatus === 'QUEUED' && <Play size={20} className="text-gray-400" />}
                  {store.jobStatus === 'RUNNING' && <Brain size={20} className="text-cyan-600 animate-pulse" />}
                  {store.jobStatus === 'COMPLETED' && <CheckCircle size={20} className="text-emerald-600" />}
                  {store.jobStatus === 'FAILED' && <AlertTriangle size={20} className="text-red-500" />}
                </div>
                <div>
                  <div className="text-sm font-semibold text-gray-900">
                    {store.jobStatus === 'QUEUED' && 'Agent 已就绪，等待启动...'}
                    {store.jobStatus === 'RUNNING' && `Agent 正在自主分析 ${store.fileCount} 份判决书...`}
                    {store.jobStatus === 'COMPLETED' && 'Agent 分析完成！即将跳转到结果页面...'}
                    {store.jobStatus === 'FAILED' && 'Agent 分析失败'}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {store.jobStatus === 'RUNNING' && (
                      <>已处理 {store.documentsProcessed}/{store.fileCount} 份 · {totalTools} 次工具调用 · {successfulTools} 成功 {failedTools > 0 ? `· ${failedTools} 失败` : ''}</>
                    )}
                    {store.agentComplete && (
                      <>总计 {store.agentComplete.total_tools_run} 次工具调用 · 节省 {store.agentComplete.total_llm_calls_saved} 次LLM · 耗时 {store.agentComplete.total_duration_seconds}s</>
                    )}
                  </div>
                </div>
              </div>
              {store.jobStatus === 'RUNNING' && (
                <div className="flex flex-wrap gap-1">
                  {Object.entries(strategyCounts).map(([s, c]) => {
                    const label = s === 'standard' ? '标准' : s === 'minimal' ? '精简' : s === 'rule_only' ? '纯规则' : '快速'
                    return <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-gray-200 text-gray-500">{label}: {c}</span>
                  })}
                </div>
              )}
            </div>
            {store.jobStatus === 'RUNNING' && store.fileCount > 0 && (
              <div className="mt-3 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-purple-500 to-amber-500"
                  animate={{ width: `${(store.documentsProcessed / store.fileCount) * 100}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            )}
          </motion.div>
        )}

        {/* Tab */}
        <div className="flex items-center gap-2 mb-4">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                activeTab === id
                  ? 'bg-gray-900 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              )}
            >
              <Icon size={16} />{label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'thoughts' && (
            <motion.div key="thoughts" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3 max-w-3xl">
              {store.thoughts.length === 0 && store.jobStatus === 'QUEUED' && (
                <div className="text-center py-16">
                  <Brain size={40} className="mx-auto mb-4 text-gray-300" />
                  <p className="text-sm text-gray-500">等待Agent启动...</p>
                  <p className="text-xs text-gray-400 mt-1">Agent将逐份感知文书结构，自主规划分析策略</p>
                </div>
              )}
              {store.thoughts.map((t, i) => (
                <AgentThoughtBubble key={i} thought={t.thought} phase={t.phase} timestamp={t.timestamp} isLatest={i === store.thoughts.length - 1 && store.jobStatus === 'RUNNING'} />
              ))}
              <div ref={thoughtEndRef} />
            </motion.div>
          )}

          {activeTab === 'decisions' && (
            <motion.div key="decisions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-[300px_1fr] gap-6">
              <div>
                <DocumentDecisionPanel
                  documents={store.docCompletions.map(d => {
                    const planThought = store.thoughts.find(t => t.documentIndex === d.document_index && t.phase === 'plan')
                    const observeThought = store.thoughts.find(t => t.documentIndex === d.document_index && t.phase === 'observe')
                    return {
                      filename: d.filename, document_index: d.document_index, quality_score: d.quality_score,
                      strategy: d.strategy_used, strategy_name: planThought?.plan?.strategy_name ?? d.strategy_used,
                      anomalies: observeThought?.profile?.anomalies ?? [],
                      tools_selected: planThought?.plan?.selected_tool_ids ?? [], tools_run: d.tools_run, errors: d.errors,
                    }
                  })}
                  selectedDoc={selectedDoc ? { ...selectedDoc, filename: selectedDoc.filename, document_index: selectedDoc.document_index, quality_score: selectedDoc.quality_score, strategy: selectedDoc.strategy_used, strategy_name: selectedDoc.strategy_used, anomalies: [], tools_selected: [], tools_run: selectedDoc.tools_run, errors: selectedDoc.errors } : null}
                  onSelect={(doc) => setSelectedDocIdx(doc.document_index)}
                  onClose={() => setSelectedDocIdx(null)}
                />
              </div>
              <div>
                {selectedDoc ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-3">
                      <FileText size={14} className="text-gray-400" />
                      <h3 className="text-sm font-semibold text-gray-800">{selectedDoc.filename}</h3>
                    </div>
                    <Card className="p-3" hover={false}>
                      <div className="flex items-center gap-2 mb-2">
                        <Lightbulb size={14} className="text-purple-500" />
                        <span className="text-xs font-medium">Agent 决策</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        策略：{selectedDoc.strategy_used} · {selectedDoc.tools_run} 工具 · {selectedDoc.errors} 错误
                      </div>
                    </Card>
                    {store.toolEvents.filter(e => e.documentIndex === selectedDoc.document_index).map((event, i) => {
                      const isLast = i === store.toolEvents.filter(e => e.documentIndex === selectedDoc.document_index).length - 1
                      if ('verified' in event) {
                        return <ToolCallCard key={i} toolId={event.tool_id} toolName={event.tool_name} phase={event.phase} status="success" durationSeconds={event.duration_seconds} outputSummary={event.output_summary} isLatest={isLast && store.jobStatus === 'RUNNING'} />
                      } else {
                        return <ToolCallCard key={i} toolId={event.tool_id} toolName={event.tool_name} phase={event.phase} status={event.will_retry ? 'retrying' : 'error'} error={event.error} isLatest={false} />
                      }
                    })}
                  </div>
                ) : (
                  <div className="text-center py-16">
                    <Shield size={32} className="mx-auto mb-3 text-gray-300" />
                    <p className="text-sm text-gray-500">选择左侧文书查看决策详情</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'overview' && (
            <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4 max-w-3xl">
              <Card className="p-5" hover={false}>
                <div className="flex items-center gap-2 mb-4">
                  <Brain size={18} className="text-cyan-600" />
                  <h3 className="text-sm font-semibold">Agent 工作循环</h3>
                </div>
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { phase: '观察', icon: Eye, colorBg: 'bg-cyan-50', colorText: 'text-cyan-600', desc: '感知文书\n编码/结构/异常' },
                    { phase: '规划', icon: Lightbulb, colorBg: 'bg-purple-50', colorText: 'text-purple-600', desc: '自主选择\n工具和策略' },
                    { phase: '执行', icon: Brain, colorBg: 'bg-amber-50', colorText: 'text-amber-600', desc: '调用工具\n记录结果' },
                    { phase: '核查', icon: CheckCircle, colorBg: 'bg-emerald-50', colorText: 'text-emerald-600', desc: '验证质量\n不通过则重试' },
                    { phase: '记录', icon: TrendingUp, colorBg: 'bg-gray-50', colorText: 'text-gray-500', desc: '写入记忆\n更新统计' },
                  ].map(({ phase, icon: Icon, colorBg, colorText, desc }) => (
                    <div key={phase} className="text-center">
                      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2', colorBg)}>
                        <Icon size={16} className={colorText} />
                      </div>
                      <div className="text-xs font-semibold text-gray-800">{phase}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5 whitespace-pre-line">{desc}</div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5" hover={false}>
                <div className="flex items-center gap-2 mb-4">
                  <Shield size={18} className="text-purple-600" />
                  <h3 className="text-sm font-semibold">Agent 策略体系</h3>
                </div>
                <div className="space-y-2">
                  {[
                    { name: '标准流程', id: 'standard', desc: '结构完整、质量好 → 16步完整分析', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
                    { name: '精简流程', id: 'minimal', desc: '质量一般或缺段落 → 跳过不可行的LLM步骤', color: 'bg-amber-50 text-amber-700 border-amber-200' },
                    { name: '纯规则', id: 'rule_only', desc: '质量差 → 仅用规则引擎，不调LLM', color: 'bg-gray-100 text-gray-600 border-gray-200' },
                    { name: '快速扫描', id: 'quick_scan', desc: '非民事文书 → 只做基础提取', color: 'bg-red-50 text-red-600 border-red-200' },
                  ].map((s) => {
                    const count = strategyCounts[s.id]
                    return (
                      <div key={s.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded border', s.color)}>{s.name}</span>
                        <div className="flex-1 text-xs text-gray-500">{s.desc}</div>
                        {count > 0 && <span className="text-xs text-gray-400">{count} 份</span>}
                      </div>
                    )
                  })}
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
