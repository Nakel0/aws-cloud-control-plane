import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface CostSummary {
  total_monthly_spend: number
  potential_monthly_savings: number
  savings_percentage: number
  findings_count: number
  findings_by_severity: Record<string, number>
  top_waste_categories: Array<{ type: string; count: number; savings: number }>
  trend_30d: Array<{ date: string; cost: number }>
}

export interface SecuritySummary {
  security_score: number
  critical_findings: number
  high_findings: number
  medium_findings: number
  low_findings: number
  compliance_status: Record<string, number>
  public_resources: number
  unencrypted_resources: number
}

export interface ReliabilitySummary {
  reliability_score: number
  single_az_resources: number
  resources_without_backup: number
  resources_without_monitoring: number
  estimated_availability: number
}

export interface DashboardData {
  account_id: string
  last_scan: string
  cost: CostSummary
  security: SecuritySummary
  reliability: ReliabilitySummary
  total_resources_scanned: number
  total_findings: number
}

export interface Finding {
  finding_id: string
  category: 'cost' | 'security' | 'reliability'
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  resource: {
    resource_id: string
    resource_type: string
    resource_name: string | null
    region: string
  }
  recommendation: string
  estimated_savings?: number
  remediation_available: boolean
  detected_at: string
}

export interface FindingsResponse {
  total: number
  offset: number
  limit: number
  findings: Finding[]
}

// API Functions
export const getDashboard = async (): Promise<DashboardData> => {
  const { data } = await api.get('/dashboard')
  return data
}

export const getCostSummary = async (): Promise<CostSummary> => {
  const { data } = await api.get('/cost/summary')
  return data
}

export const getCostByService = async (): Promise<Record<string, number>> => {
  const { data } = await api.get('/cost/by-service')
  return data
}

export const getSecuritySummary = async (): Promise<SecuritySummary> => {
  const { data } = await api.get('/security/summary')
  return data
}

export const getReliabilitySummary = async (): Promise<ReliabilitySummary> => {
  const { data } = await api.get('/reliability/summary')
  return data
}

export const getFindings = async (
  category?: string,
  severity?: string,
  limit = 100,
  offset = 0
): Promise<FindingsResponse> => {
  const params = new URLSearchParams()
  if (category) params.append('category', category)
  if (severity) params.append('severity', severity)
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())
  
  const { data } = await api.get(`/findings?${params}`)
  return data
}

export const remediate = async (
  findingId: string,
  dryRun = true
): Promise<{ status: string; result_message: string }> => {
  const { data } = await api.post(`/remediate/${findingId}?dry_run=${dryRun}`)
  return data
}

export const startScan = async (regions: string[] = ['us-east-1']) => {
  const { data } = await api.post('/scans', { regions })
  return data
}

export const getScanStatus = async (scanId: string) => {
  const { data } = await api.get(`/scans/${scanId}`)
  return data
}

export default api
