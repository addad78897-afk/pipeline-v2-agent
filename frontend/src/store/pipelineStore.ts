import { create } from 'zustand'
import type { JobStatus, StepState } from '@/utils/constants'

interface PipelineState {
  jobId: string | null
  jobStatus: JobStatus | null
  progressPercent: number
  currentStep: number
  steps: StepState[]
  connected: boolean

  setJob: (jobId: string) => void
  updateProgress: (percent: number, currentStep: number) => void
  updateStep: (stepNumber: number, update: Partial<StepState>) => void
  setConnected: (connected: boolean) => void
  reset: () => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  jobId: null,
  jobStatus: null,
  progressPercent: 0,
  currentStep: 0,
  steps: [],
  connected: false,

  setJob: (jobId) => set({ jobId, jobStatus: 'QUEUED', progressPercent: 0, currentStep: 0 }),
  updateProgress: (progressPercent, currentStep) => set({ progressPercent, currentStep, jobStatus: 'RUNNING' }),
  updateStep: (stepNumber, update) =>
    set((state) => ({
      steps: state.steps.map((s) => (s.number === stepNumber ? { ...s, ...update } : s)),
    })),
  setConnected: (connected) => set({ connected }),
  reset: () => set({ jobId: null, jobStatus: null, progressPercent: 0, currentStep: 0, steps: [], connected: false }),
}))
