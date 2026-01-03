import { useState } from 'react'
import { Search, Filter, Download } from 'lucide-react'
import FindingCard from '../components/FindingCard'
import type { Finding } from '../services/api'

// Combined demo data
const allFindings: Finding[] = [
  // Cost findings
  {
    finding_id: 'cost-idle-ec2-i-abc123',
    category: 'cost',
    severity: 'high',
    title: 'Idle EC2 Instance: prod-worker-3',
    description: 'Instance m5.xlarge has average CPU utilization of 1.8% over the past 14 days.',
    resource: {
      resource_id: 'i-abc123',
      resource_type: 'ec2:instance',
      resource_name: 'prod-worker-3',
      region: 'us-east-1',
    },
    recommendation: 'Stop or terminate this instance to save $140.16/month.',
    estimated_savings: 140.16,
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'cost-unattached-ebs-vol-789',
    category: 'cost',
    severity: 'medium',
    title: 'Unattached EBS Volume: vol-789xyz',
    description: '500GB gp3 volume has been unattached for 45 days.',
    resource: {
      resource_id: 'vol-789xyz',
      resource_type: 'ebs:volume',
      resource_name: null,
      region: 'us-east-1',
    },
    recommendation: 'Delete this volume if data is no longer needed.',
    estimated_savings: 40.00,
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  // Security findings
  {
    finding_id: 'security-public-s3-data-bucket',
    category: 'security',
    severity: 'critical',
    title: 'Public S3 Bucket: customer-data-prod',
    description: 'S3 bucket allows public access via ACL. This exposes sensitive data to the internet.',
    resource: {
      resource_id: 'customer-data-prod',
      resource_type: 's3:bucket',
      resource_name: 'customer-data-prod',
      region: 'global',
    },
    recommendation: 'Enable S3 Block Public Access and review bucket ACL.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'security-root-no-mfa',
    category: 'security',
    severity: 'critical',
    title: 'Root Account MFA Not Enabled',
    description: 'The AWS root account does not have MFA enabled. This is a critical security risk.',
    resource: {
      resource_id: 'root',
      resource_type: 'iam:user',
      resource_name: 'root',
      region: 'global',
    },
    recommendation: 'Enable MFA on the root account immediately.',
    remediation_available: false,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'security-open-sg-web',
    category: 'security',
    severity: 'high',
    title: 'Open Security Group: sg-webservers',
    description: 'Security group allows SSH (22) access from 0.0.0.0/0.',
    resource: {
      resource_id: 'sg-12345678',
      resource_type: 'ec2:security-group',
      resource_name: 'sg-webservers',
      region: 'us-east-1',
    },
    recommendation: 'Restrict SSH access to specific IP ranges.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  // Reliability findings
  {
    finding_id: 'reliability-single-az-rds-prod',
    category: 'reliability',
    severity: 'high',
    title: 'Single-AZ RDS Instance: production-db',
    description: 'RDS instance is deployed in a single AZ (us-east-1a), creating a single point of failure.',
    resource: {
      resource_id: 'production-db',
      resource_type: 'rds:instance',
      resource_name: 'production-db',
      region: 'us-east-1',
    },
    recommendation: 'Enable Multi-AZ deployment for automatic failover.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'reliability-no-backup-rds-analytics',
    category: 'reliability',
    severity: 'critical',
    title: 'RDS Without Backups: analytics-db',
    description: 'RDS instance has automated backups disabled. Data loss risk!',
    resource: {
      resource_id: 'analytics-db',
      resource_type: 'rds:instance',
      resource_name: 'analytics-db',
      region: 'us-east-1',
    },
    recommendation: 'Enable automated backups with at least 7 days retention.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
]

export default function Findings() {
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<string>('all')

  const filteredFindings = allFindings.filter((finding) => {
    const matchesSearch = 
      finding.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      finding.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesCategory = categoryFilter === 'all' || finding.category === categoryFilter
    const matchesSeverity = severityFilter === 'all' || finding.severity === severityFilter

    return matchesSearch && matchesCategory && matchesSeverity
  })

  const sortedFindings = [...filteredFindings].sort((a, b) => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    return severityOrder[a.severity] - severityOrder[b.severity]
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Findings</h1>
          <p className="text-gray-500">
            {filteredFindings.length} findings across all categories
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search findings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Categories</option>
              <option value="cost">Cost</option>
              <option value="security">Security</option>
              <option value="reliability">Reliability</option>
            </select>
          </div>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Quick Stats */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-100">
          <span className="text-sm text-gray-500">Quick filters:</span>
          <button
            onClick={() => {
              setCategoryFilter('all')
              setSeverityFilter('critical')
            }}
            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded-full hover:bg-red-200 transition-colors"
          >
            Critical ({allFindings.filter(f => f.severity === 'critical').length})
          </button>
          <button
            onClick={() => {
              setCategoryFilter('security')
              setSeverityFilter('all')
            }}
            className="px-3 py-1 text-sm bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
          >
            Security ({allFindings.filter(f => f.category === 'security').length})
          </button>
          <button
            onClick={() => {
              setCategoryFilter('cost')
              setSeverityFilter('all')
            }}
            className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
          >
            Cost ({allFindings.filter(f => f.category === 'cost').length})
          </button>
          <button
            onClick={() => {
              const fixableFindings = allFindings.filter(f => f.remediation_available)
              alert(`${fixableFindings.length} findings can be auto-remediated`)
            }}
            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
          >
            Auto-fixable ({allFindings.filter(f => f.remediation_available).length})
          </button>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {sortedFindings.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="text-gray-400 mb-2">No findings match your filters</div>
            <button
              onClick={() => {
                setSearchQuery('')
                setCategoryFilter('all')
                setSeverityFilter('all')
              }}
              className="text-primary-600 hover:text-primary-700"
            >
              Clear filters
            </button>
          </div>
        ) : (
          sortedFindings.map((finding) => (
            <FindingCard
              key={finding.finding_id}
              finding={finding}
              onRemediate={(id) => console.log('Remediate:', id)}
            />
          ))
        )}
      </div>

      {/* Summary */}
      {sortedFindings.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4 text-center text-sm text-gray-500">
          Showing {sortedFindings.length} of {allFindings.length} findings
          {(categoryFilter !== 'all' || severityFilter !== 'all' || searchQuery) && (
            <button
              onClick={() => {
                setSearchQuery('')
                setCategoryFilter('all')
                setSeverityFilter('all')
              }}
              className="ml-2 text-primary-600 hover:text-primary-700"
            >
              Clear filters
            </button>
          )}
        </div>
      )}
    </div>
  )
}
