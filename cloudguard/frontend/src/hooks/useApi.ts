import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
  })
}

export function useCostSummary() {
  return useQuery({
    queryKey: ['cost-summary'],
    queryFn: api.getCostSummary,
  })
}

export function useCostByService() {
  return useQuery({
    queryKey: ['cost-by-service'],
    queryFn: api.getCostByService,
  })
}

export function useSecuritySummary() {
  return useQuery({
    queryKey: ['security-summary'],
    queryFn: api.getSecuritySummary,
  })
}

export function useReliabilitySummary() {
  return useQuery({
    queryKey: ['reliability-summary'],
    queryFn: api.getReliabilitySummary,
  })
}

export function useFindings(category?: string, severity?: string) {
  return useQuery({
    queryKey: ['findings', category, severity],
    queryFn: () => api.getFindings(category, severity),
  })
}

export function useRemediate() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ findingId, dryRun }: { findingId: string; dryRun: boolean }) =>
      api.remediate(findingId, dryRun),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useScan() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (regions: string[]) => api.startScan(regions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
