import { useParams, useNavigate } from 'react-router-dom'
import { PipelineFlow } from '@/components/pipeline/PipelineFlow'
import { StepDetailPanel } from '@/components/pipeline/StepDetailPanel'
import { usePipelineStore } from '@/store/pipelineStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import { STEPS } from '@/utils/constants'
import { useState, useEffect } from 'react'

export function PipelinePage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const { currentStep, steps, jobStatus } = usePipelineStore()
  const [selectedStep, setSelectedStep] = useState<number | null>(null)

  // 页面加载初始化
  useEffect(() => {
    if (jobId && !usePipelineStore.getState().jobId) {
      usePipelineStore.getState().setJob(jobId)
    }
  }, [jobId])

  // 连接WebSocket获取实时进度
  useWebSocket(jobId ?? null)

  // 完成后自动跳转结果页
  useEffect(() => {
    if (jobStatus === 'COMPLETED' && jobId) {
      const timer = setTimeout(() => navigate(`/results/${jobId}`), 2000)
      return () => clearTimeout(timer)
    }
  }, [jobStatus, jobId, navigate])

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-auto p-6">
        {jobStatus === 'COMPLETED' && (
          <div className="mb-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
            <p className="text-sm text-emerald-700 font-medium">管线执行完成！即将跳转到结果页面...</p>
          </div>
        )}
        <PipelineFlow
          steps={STEPS.map((s) => ({
            ...s,
            status: steps.find((st) => st.number === s.number)?.status ?? 'PENDING',
            log: steps.find((st) => st.number === s.number)?.log ?? [],
          }))}
          activeStep={currentStep}
          onStepClick={(step) => setSelectedStep(step.number)}
        />
      </div>
      {selectedStep && (
        <StepDetailPanel
          step={STEPS.find((s) => s.number === selectedStep)!}
          stepState={
            steps.find((s) => s.number === selectedStep) ?? {
              number: selectedStep,
              status: 'PENDING' as const,
              log: [],
            }
          }
          onClose={() => setSelectedStep(null)}
        />
      )}
    </div>
  )
}
