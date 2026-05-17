import { api } from './client'

export async function runPipeline(
  sessionId: string,
  phases?: number[]
): Promise<{ job_id: string; status: string }> {
  const { data } = await api.post('/pipeline/run', {
    session_id: sessionId,
    phase_selection: phases ?? null,
  })
  return data
}

export async function getPipelineStatus(jobId: string) {
  const { data } = await api.get(`/pipeline/status/${jobId}`)
  return data
}
