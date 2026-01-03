import { DollarSign, TrendingDown, Server, HardDrive, Cloud } from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import StatCard from '../components/StatCard'
import FindingCard from '../components/FindingCard'

const costByService = [
  { service: 'EC2', cost: 4520 },
  { service: 'RDS', cost: 3200 },
  { service: 'S3', cost: 1800 },
  { service: 'Lambda', cost: 890 },
  { service: 'ELB', cost: 650 },
  { service: 'Other', cost: 1390 },
]

const wasteBreakdown = [
  { name: 'Idle Resources', value: 1240, color: '#EF4444' },
  { name: 'Oversized', value: 680, color: '#F59E0B' },
  { name: 'Unattached', value: 320, color: '#3B82F6' },
  { name: 'Old Snapshots', value: 100, color: '#8B5CF6' },
]

const costFindings = [
  {
    finding_id: 'cost-idle-ec2-i-abc123',
    category: 'cost' as const,
    severity: 'high' as const,
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
    finding_id: 'cost-oversized-ec2-i-def456',
    category: 'cost' as const,
    severity: 'medium' as const,
    title: 'Oversized Instance: api-server-1',
    description: 'Instance c5.2xlarge has peak CPU of 35%. Consider downsizing to c5.xlarge.',
    resource: {
      resource_id: 'i-def456',
      resource_type: 'ec2:instance',
      resource_name: 'api-server-1',
      region: 'us-east-1',
    },
    recommendation: 'Rightsize from c5.2xlarge to c5.xlarge.',
    estimated_savings: 124.10,
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'cost-unattached-ebs-vol-789',
    category: 'cost' as const,
    severity: 'medium' as const,
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
  {
    finding_id: 'cost-ri-opportunity-m5',
    category: 'cost' as const,
    severity: 'high' as const,
    title: 'Reserved Instance Opportunity: m5.large',
    description: 'Running 5 on-demand m5.large instances consistently. RI could save 40%.',
    resource: {
      resource_id: 'ri-m5-large',
      resource_type: 'ec2:instance',
      resource_name: 'm5.large fleet',
      region: 'us-east-1',
    },
    recommendation: 'Purchase 1-year Reserved Instances for m5.large.',
    estimated_savings: 280.00,
    remediation_available: false,
    detected_at: new Date().toISOString(),
  },
]

export default function CostOptimization() {
  const totalWaste = wasteBreakdown.reduce((sum, item) => sum + item.value, 0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cost Optimization</h1>
        <p className="text-gray-500">Identify and eliminate cloud waste</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Monthly Spend"
          value="$12,450"
          subtitle="Current month to date"
          icon={<DollarSign className="w-6 h-6" />}
        />
        <StatCard
          title="Potential Savings"
          value={`$${totalWaste.toLocaleString()}`}
          subtitle={`${((totalWaste / 12450) * 100).toFixed(1)}% of total spend`}
          icon={<TrendingDown className="w-6 h-6" />}
          variant="success"
        />
        <StatCard
          title="Idle Resources"
          value="8"
          subtitle="$1,240/mo wasted"
          icon={<Server className="w-6 h-6" />}
          variant="warning"
        />
        <StatCard
          title="Unattached Storage"
          value="1.2 TB"
          subtitle="$320/mo in orphaned volumes"
          icon={<HardDrive className="w-6 h-6" />}
          variant="warning"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost by Service */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Cost by Service</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={costByService} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis type="number" tickFormatter={(v) => `$${v}`} stroke="#9CA3AF" fontSize={12} />
                <YAxis type="category" dataKey="service" stroke="#9CA3AF" fontSize={12} width={60} />
                <Tooltip
                  formatter={(value: number) => [`$${value.toLocaleString()}`, 'Cost']}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="cost" fill="#6366F1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Waste Breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Waste Breakdown</h2>
          <div className="flex items-center">
            <div className="h-48 w-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={wasteBreakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {wasteBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [`$${value}`, 'Waste']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-3 ml-6">
              {wasteBreakdown.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm text-gray-600">{item.name}</span>
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    ${item.value}/mo
                  </span>
                </div>
              ))}
              <div className="pt-2 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">Total Waste</span>
                  <span className="text-lg font-bold text-red-600">
                    ${totalWaste}/mo
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Findings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Cost Optimization Findings</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">{costFindings.length} findings</span>
            <select className="text-sm border border-gray-200 rounded-lg px-3 py-1.5">
              <option>All severities</option>
              <option>Critical</option>
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>
          </div>
        </div>
        <div className="space-y-3">
          {costFindings.map((finding) => (
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
