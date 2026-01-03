import { Activity, Server, Database, HardDrive, Bell } from 'lucide-react'
import StatCard from '../components/StatCard'
import ScoreGauge from '../components/ScoreGauge'
import FindingCard from '../components/FindingCard'

const reliabilityFindings = [
  {
    finding_id: 'reliability-single-az-rds-prod',
    category: 'reliability' as const,
    severity: 'high' as const,
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
    category: 'reliability' as const,
    severity: 'critical' as const,
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
  {
    finding_id: 'reliability-no-asg-worker',
    category: 'reliability' as const,
    severity: 'medium' as const,
    title: 'EC2 Without Auto Scaling: worker-node-1',
    description: 'EC2 instance is not part of an Auto Scaling group. No automatic recovery.',
    resource: {
      resource_id: 'i-worker123',
      resource_type: 'ec2:instance',
      resource_name: 'worker-node-1',
      region: 'us-east-1',
    },
    recommendation: 'Consider using Auto Scaling for automatic replacement and scaling.',
    remediation_available: false,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'reliability-no-alarm-api',
    category: 'reliability' as const,
    severity: 'medium' as const,
    title: 'EC2 Without CloudWatch Alarms: api-server',
    description: 'EC2 instance has no CloudWatch alarms configured. Issues may go unnoticed.',
    resource: {
      resource_id: 'i-api123',
      resource_type: 'ec2:instance',
      resource_name: 'api-server',
      region: 'us-east-1',
    },
    recommendation: 'Create CloudWatch alarms for CPU, memory, and disk metrics.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'reliability-no-snapshot-vol',
    category: 'reliability' as const,
    severity: 'medium' as const,
    title: 'EBS Without Recent Snapshot: vol-data123',
    description: 'EBS volume (500GB) has no snapshots in the last 30 days.',
    resource: {
      resource_id: 'vol-data123',
      resource_type: 'ebs:volume',
      resource_name: 'app-data',
      region: 'us-east-1',
    },
    recommendation: 'Create regular snapshots using AWS Backup or Data Lifecycle Manager.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
]

export default function Reliability() {
  const criticalCount = reliabilityFindings.filter(f => f.severity === 'critical').length
  const highCount = reliabilityFindings.filter(f => f.severity === 'high').length

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reliability</h1>
        <p className="text-gray-500">Improve resilience and availability of your infrastructure</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Reliability Score"
          value="85/100"
          subtitle="Good standing"
          icon={<Activity className="w-6 h-6" />}
          variant="success"
        />
        <StatCard
          title="Single-AZ Resources"
          value="4"
          subtitle="At risk during AZ failure"
          icon={<Server className="w-6 h-6" />}
          variant="warning"
        />
        <StatCard
          title="No Backups"
          value="2"
          subtitle="Databases without backups"
          icon={<Database className="w-6 h-6" />}
          variant="danger"
        />
        <StatCard
          title="No Monitoring"
          value="6"
          subtitle="Resources without alarms"
          icon={<Bell className="w-6 h-6" />}
        />
      </div>

      {/* Reliability Score & Availability */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reliability Score */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Reliability Score</h2>
          <div className="flex justify-center mb-6">
            <ScoreGauge score={85} label="Overall Score" size="lg" />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">High Availability</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-yellow-500" style={{ width: '70%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">70%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Backup Coverage</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '85%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">85%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Auto-Recovery</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '90%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">90%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Monitoring</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-yellow-500" style={{ width: '75%' }} />
                </div>
                <span className="text-sm font-medium text-gray-900">75%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Availability Estimation */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Estimated Availability</h2>
          <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">99.95%</div>
              <div className="text-sm text-gray-500 mt-1">Current Estimate</div>
              <div className="text-xs text-gray-400">~4.38 hours downtime/year</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-primary-600">99.99%</div>
              <div className="text-sm text-gray-500 mt-1">After Fixes</div>
              <div className="text-xs text-gray-400">~52 minutes downtime/year</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-gray-400">99.999%</div>
              <div className="text-sm text-gray-500 mt-1">Target (5 nines)</div>
              <div className="text-xs text-gray-400">~5 minutes downtime/year</div>
            </div>
          </div>
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
            <h3 className="font-medium text-blue-900 mb-2">Recommendations to Reach 99.99%</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Enable Multi-AZ for all production RDS instances</li>
              <li>• Configure automated backups for all databases</li>
              <li>• Add CloudWatch alarms for all critical resources</li>
              <li>• Implement Auto Scaling for stateless workloads</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Reliability Findings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Reliability Findings</h2>
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
          {reliabilityFindings.map((finding) => (
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
