import { X, Clock, FileCode, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/shared/Badge'
import type { StepDefinition, StepState } from '@/utils/constants'

interface StepDetailPanelProps {
  step: StepDefinition
  stepState: StepState
  onClose: () => void
}

export function StepDetailPanel({ step, stepState, onClose }: StepDetailPanelProps) {
  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 20 }}
        className="w-80 shrink-0 border-l border-gray-200 bg-white overflow-auto shadow-lg"
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-4">
            <Badge status={stepState.status} />
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
              <X size={16} />
            </button>
          </div>

          <h3 className="text-sm font-semibold text-gray-900 mb-1">{step.name}</h3>
          <div className="text-xs text-gray-400 mb-4">Step {step.number} · {step.script}</div>

          <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 mb-4">
            <p className="text-xs text-gray-600 leading-relaxed">{step.description}</p>
          </div>

          {stepState.startedAt && (
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
              <Clock size={12} />
              开始：{new Date(stepState.startedAt).toLocaleTimeString()}
            </div>
          )}
          {stepState.completedAt && (
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
              <Clock size={12} />
              完成：{new Date(stepState.completedAt).toLocaleTimeString()}
            </div>
          )}

          {stepState.error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
              <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-xs text-red-600">{stepState.error}</p>
            </div>
          )}

          {stepState.log.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <FileCode size={12} />
                输出日志
              </div>
              <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 font-mono text-[11px] text-gray-700 max-h-48 overflow-auto space-y-0.5">
                {stepState.log.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  )
}
