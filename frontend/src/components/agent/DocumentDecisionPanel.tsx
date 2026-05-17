import { motion, AnimatePresence } from 'framer-motion'
import { FileText, X, Shield, AlertTriangle, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'

interface DocDecision {
  filename: string
  document_index: number
  quality_score: number
  strategy: string
  strategy_name: string
  anomalies: string[]
  tools_selected: string[]
  tools_run: number
  errors: number
}

interface Props {
  documents: DocDecision[]
  selectedDoc: DocDecision | null
  onSelect: (doc: DocDecision) => void
  onClose: () => void
}

const strategyBadge: Record<string, { label: string; color: string }> = {
  standard: { label: '标准', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-400/20' },
  minimal: { label: '精简', color: 'bg-amber-500/10 text-amber-400 border-amber-400/20' },
  rule_only: { label: '纯规则', color: 'bg-slate-500/10 text-slate-400 border-slate-400/20' },
  quick_scan: { label: '快速', color: 'bg-red-500/10 text-red-400 border-red-400/20' },
}

export function DocumentDecisionPanel({ documents, selectedDoc, onSelect, onClose }: Props) {
  return (
    <div className="space-y-2">
      {documents.map((doc) => {
        const badge = strategyBadge[doc.strategy] ?? strategyBadge.standard
        return (
          <motion.button
            key={doc.document_index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={() => onSelect(doc)}
            className={cn(
              'w-full text-left p-3 rounded-lg border transition-colors',
              selectedDoc?.document_index === doc.document_index
                ? 'border-cyan-400/30 bg-cyan-500/10'
                : 'border-transparent bg-white/5 hover:bg-white/10'
            )}
          >
            <div className="flex items-start gap-2.5">
              <FileText size={14} className="text-[var(--color-text-muted)] shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-[var(--color-text-primary)] truncate">
                  {doc.filename}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn('text-[10px] px-1.5 py-0.5 rounded border', badge.color)}>
                    {badge.label}
                  </span>
                  {doc.quality_score < 0.5 && (
                    <span className="text-[10px] text-amber-400 flex items-center gap-0.5">
                      <AlertTriangle size={10} />
                      质量{doc.quality_score.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-[var(--color-text-muted)]">
                  <span>{doc.tools_run} 工具</span>
                  {doc.errors > 0 && (
                    <span className="text-red-400">{doc.errors} 错误</span>
                  )}
                </div>
              </div>
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
