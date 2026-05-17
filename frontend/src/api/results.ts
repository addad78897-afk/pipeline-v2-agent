import { api } from './client'

export async function getSummary(jobId: string) {
  const { data } = await api.get(`/results/${jobId}/summary`)
  return data
}

export async function getDimensions(jobId: string, page = 1, perPage = 50) {
  const { data } = await api.get(`/results/${jobId}/dimensions`, {
    params: { page, per_page: perPage },
  })
  return data
}

export async function getCharts(jobId: string) {
  const { data } = await api.get(`/results/${jobId}/charts`)
  return data
}

export async function getReports(jobId: string) {
  const { data } = await api.get(`/results/${jobId}/reports`)
  return data
}

export async function getHistory(page = 1) {
  const { data } = await api.get('/history', { params: { page } })
  return data
}
