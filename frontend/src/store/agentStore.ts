import { create } from 'zustand'

export type AgentPhase = 'observe' | 'plan' | 'execute' | 'verify' | 'record'
export type AgentJobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface AgentThought {
  timestamp: number
  thought: string
  phase: AgentPhase
  documentIndex?: number
  profile?: {
    encoding: string
    quality_score: number
    doc_type: string
    trial_level: string
    anomalies: string[]
    has_sections: Record<string, boolean>
  }
  plan?: {
    strategy: string
    strategy_name: string
    strategy_reason: string
    selected_tool_ids: string[]
    skipped_tools: string[]
    estimated_llm_calls: number
  }
}

export interface ToolEvent {
  timestamp: number
  documentIndex: number
  tool_id: string
  tool_name: string
  phase: number
}

export interface ToolCompleteEvent extends ToolEvent {
  duration_seconds: number
  output_summary: string
  verified: boolean
}

export interface ToolErrorEvent extends ToolEvent {
  error: string
  will_retry: boolean
}

export interface DocComplete {
  document_index: number
  filename: string
  quality_score: number
  strategy_used: string
  tools_run: number
  errors: number
}

export interface AgentComplete {
  total_files: number
  total_tools_run: number
  total_llm_calls_saved: number
  total_duration_seconds: number
  avg_duration_per_doc: number
}

interface AgentState {
  jobId: string | null
  jobStatus: AgentJobStatus | null
  fileCount: number
  documentsProcessed: number
  thoughts: AgentThought[]
  toolEvents: (ToolCompleteEvent | ToolErrorEvent)[]
  docCompletions: DocComplete[]
  agentComplete: AgentComplete | null
  connected: boolean

  setJob: (jobId: string, fileCount: number) => void
  addThought: (thought: AgentThought) => void
  addToolComplete: (event: ToolCompleteEvent) => void
  addToolError: (event: ToolErrorEvent) => void
  addDocComplete: (event: DocComplete) => void
  setAgentComplete: (event: AgentComplete) => void
  setConnected: (connected: boolean) => void
  incrementDocumentsProcessed: () => void
  reset: () => void
}

export const useAgentStore = create<AgentState>((set) => ({
  jobId: null,
  jobStatus: null,
  fileCount: 0,
  documentsProcessed: 0,
  thoughts: [],
  toolEvents: [],
  docCompletions: [],
  agentComplete: null,
  connected: false,

  setJob: (jobId, fileCount) =>
    set({ jobId, fileCount, jobStatus: 'QUEUED', documentsProcessed: 0, thoughts: [], toolEvents: [], docCompletions: [], agentComplete: null }),
  addThought: (thought) =>
    set((s) => ({ thoughts: [...s.thoughts, thought], jobStatus: 'RUNNING' })),
  addToolComplete: (event) =>
    set((s) => ({ toolEvents: [...s.toolEvents, event] })),
  addToolError: (event) =>
    set((s) => ({ toolEvents: [...s.toolEvents, event] })),
  addDocComplete: (event) =>
    set((s) => ({ docCompletions: [...s.docCompletions, event] })),
  setAgentComplete: (event) =>
    set({ agentComplete: event, jobStatus: 'COMPLETED' }),
  setConnected: (connected) => set({ connected }),
  incrementDocumentsProcessed: () =>
    set((s) => ({ documentsProcessed: s.documentsProcessed + 1 })),
  reset: () =>
    set({ jobId: null, jobStatus: null, fileCount: 0, documentsProcessed: 0, thoughts: [], toolEvents: [], docCompletions: [], agentComplete: null, connected: false }),
}))
