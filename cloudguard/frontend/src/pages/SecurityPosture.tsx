import { Shield, Lock, Globe, Key, AlertTriangle } from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts'
import StatCard from '../components/StatCard'
import ScoreGauge from '../components/ScoreGauge'
import FindingCard from '../components/FindingCard'

const complianceData = [
  { framework: 'CIS AWS', score: 75, color: '#10B981' },
  { framework: 'SOC2', score: 82, color: '#3B82F6' },
  { framework: 'PCI-DSS', score: 68, color: '#F59E0B' },
  { framework: 'HIPAA', score: 71, color: '#8B5CF6' },
]

const securityFindings = [
  {
    finding_id: 'security-public-s3-data-bucket',
    category: 'security' as const,
    severity: 'critical' as const,
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
    category: 'security' as const,
    severity: 'critical' as const,
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
    category: 'security' as const,
    severity: 'high' as const,
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
  {
    finding_id: 'security-unencrypted-rds',
    category: 'security' as const,
    severity: 'high' as const,
    title: 'Unencrypted RDS Instance: production-db',
    description: 'RDS instance does not have storage encryption enabled.',
    resource: {
      resource_id: 'production-db',
      resource_type: 'rds:instance',
      resource_name: 'production-db',
      region: 'us-east-1',
    },
    recommendation: 'Create encrypted snapshot and restore to encrypted instance.',
    remediation_available: false,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'security-unused-key-AKIA123',
    category: 'security' as const,
    severity: 'medium' as const,
    title: 'Unused Access Key: AKIA123...',
    description: 'Access key for user deploy-bot has not been used in 120 days.',
    resource: {
      resource_id: 'AKIA123...',
      resource_type: 'iam:user',
      resource_name: 'deploy-bot',
      region: 'global',
    },
    recommendation: 'Deactivate or delete this unused access key.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
]

export default function SecurityPosture() {
  const criticalCount = securityFindings.filter(f => f.severity === 'critical').length
  const highCount = securityFindings.filter(f => f.severity === 'high').length

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Security Posture</h1>
        <p className="text-gray-500">Identify and fix security misconfigurations</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Security Score"
          value="72/100"
          subtitle="Needs improvement"
          icon={<Shield className="w-6 h-6" />}
          variant="warning"
        />
        <StatCard
          title="Critical Issues"
          value={criticalCount.toString()}
          subtitle="Require immediate action"
          icon={<AlertTriangle className="w-6 h-6" />}
          variant="danger"
        />
        <StatCard
          title="Public Resources"
          value="3"
          subtitle="Exposed to internet"
          icon={<Globe className="w-6 h-6" />}
          variant="warning"
        />
        <StatCard
          title="IAM Issues"
          value="5"
          subtitle="Credential & permission issues"
          icon={<Key className="w-6 h-6" />}
        />
      </div>

      {/* Security Score & Compliance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Security Score Breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Security Score</h2>
          <div className="flex justify-center mb-6">
            <ScoreGauge score={72} label="Overall Score" size="lg" />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Public Access</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{ width: '30%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">30%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Encryption</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-yellow-500" style={{ width: '65%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">65%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">IAM Best Practices</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '80%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">80%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Network Security</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-yellow-500" style={{ width: '55%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">55%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Compliance Status */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Compliance Status</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={complianceData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis type="number" domain={[0, 100]} stroke="#9CA3AF" fontSize={12} />
                <YAxis type="category" dataKey="framework" stroke="#9CA3AF" fontSize={12} width={80} />
                <Tooltip
                  formatter={(value: number) => [`${value}%`, 'Compliance']}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                  }}
                />
                <Bar 
                  dataKey="score" 
                  radius={[0, 4, 4, 0]}
                  fill="#6366F1"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-4 text-center">
            {complianceData.map((item) => (
              <div key={item.framework}>
                <div className="text-2xl font-bold" style={{ color: item.color }}>
                  {item.score}%
                </div>
                <div className="text-xs text-gray-500">{item.framework}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Security Findings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Security Findings</h2>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                {criticalCount} Critical
              </span>
              <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded-full">
                {highCount} High
              </span>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {securityFindings.map((finding) => (
            <FindingCard
              key={finding.finding_id}
              finding={finding}
              onRemediate={(id) => console.log('Remediate:', id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
