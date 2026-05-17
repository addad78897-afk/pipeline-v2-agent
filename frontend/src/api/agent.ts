import { api } from './client'

export async function runAgent(sessionId: string) {
  const { data } = await api.post('/agent/run', { session_id: sessionId })
  return data as { job_id: string; status: string; file_count: number; mode: string }
}

export async function getAgentStatus(jobId: string) {
  const { data } = await api.get(`/agent/status/${jobId}`)
  return data
}

export async function getAgentMemory() {
  const { data } = await api.get('/agent/memory')
  return data
}

export async function getAgentDocuments(jobId: string) {
  const { data } = await api.get(`/agent/job/${jobId}/documents`)
  return data
}
