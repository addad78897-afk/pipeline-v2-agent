import { useQuery } from '@tanstack/react-query'
import { getSummary, getDimensions, getCharts, getReports } from '@/api/results'

export function useSummary(jobId: string | undefined) {
  return useQuery({
    queryKey: ['summary', jobId],
    queryFn: () => getSummary(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  })
}

export function useDimensions(jobId: string | undefined, page = 1, perPage = 50) {
  return useQuery({
    queryKey: ['dimensions', jobId, page, perPage],
    queryFn: () => getDimensions(jobId!, page, perPage),
    enabled: !!jobId,
    staleTime: 60_000,
  })
}

export function useCharts(jobId: string | undefined) {
  return useQuery({
    queryKey: ['charts', jobId],
    queryFn: () => getCharts(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  })
}

export function useReportsData(jobId: string | undefined) {
  return useQuery({
    queryKey: ['reports', jobId],
    queryFn: () => getReports(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  })
}
