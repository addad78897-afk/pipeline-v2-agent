import { motion } from 'framer-motion'
import { FileText, AlertTriangle } from 'lucide-react'
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
  standard: { label: '标准', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  minimal: { label: '精简', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  rule_only: { label: '纯规则', color: 'bg-gray-100 text-gray-600 border-gray-200' },
  quick_scan: { label: '快速', color: 'bg-red-50 text-red-600 border-red-200' },
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
                ? 'border-cyan-300 bg-cyan-50 shadow-sm'
                : 'border-gray-100 bg-white hover:bg-gray-50 hover:border-gray-200'
            )}
          >
            <div className="flex items-start gap-2.5">
              <FileText size={14} className="text-gray-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-gray-800 truncate">{doc.filename}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn('text-[10px] px-1.5 py-0.5 rounded border', badge.color)}>
                    {badge.label}
                  </span>
                  {doc.quality_score < 0.5 && (
                    <span className="text-[10px] text-amber-600 flex items-center gap-0.5">
                      <AlertTriangle size={10} />质量{doc.quality_score.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-gray-400">
                  <span>{doc.tools_run} 工具</span>
                  {doc.errors > 0 && <span className="text-red-500">{doc.errors} 错误</span>}
                </div>
              </div>
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
