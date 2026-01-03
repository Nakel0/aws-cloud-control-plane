import { 
  DollarSign, 
  Shield, 
  Activity, 
  AlertTriangle,
  TrendingDown,
  Lock,
  Server,
  RefreshCw
} from 'lucide-react'
import { 
  AreaChart, 
  Area, 
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
import ScoreGauge from '../components/ScoreGauge'
import FindingCard from '../components/FindingCard'

// Demo data (replace with API calls in production)
const costTrend = [
  { date: 'Dec 1', cost: 12500 },
  { date: 'Dec 5', cost: 13200 },
  { date: 'Dec 10', cost: 12800 },
  { date: 'Dec 15', cost: 14500 },
  { date: 'Dec 20', cost: 13900 },
  { date: 'Dec 25', cost: 12100 },
  { date: 'Dec 30', cost: 11800 },
]

const findingsByCategory = [
  { name: 'Cost', value: 24, color: '#10B981' },
  { name: 'Security', value: 12, color: '#EF4444' },
  { name: 'Reliability', value: 8, color: '#3B82F6' },
]

const topFindings = [
  {
    finding_id: 'cost-idle-ec2-i-1234567890',
    category: 'cost' as const,
    severity: 'high' as const,
    title: 'Idle EC2 Instance: i-1234567890',
    description: 'Instance has average CPU utilization of 2.3% over the past 7 days.',
    resource: {
      resource_id: 'i-1234567890',
      resource_type: 'ec2:instance',
      resource_name: 'web-server-prod-1',
      region: 'us-east-1',
    },
    recommendation: 'Consider stopping or terminating this instance.',
    estimated_savings: 156.80,
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'security-public-s3-my-bucket',
    category: 'security' as const,
    severity: 'critical' as const,
    title: 'Public S3 Bucket: my-data-bucket',
    description: 'S3 bucket allows public access via ACL.',
    resource: {
      resource_id: 'my-data-bucket',
      resource_type: 's3:bucket',
      resource_name: 'my-data-bucket',
      region: 'global',
    },
    recommendation: 'Enable S3 Block Public Access settings.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
  {
    finding_id: 'reliability-single-az-rds-mydb',
    category: 'reliability' as const,
    severity: 'high' as const,
    title: 'Single-AZ RDS Instance: mydb',
    description: 'RDS instance is deployed in a single AZ, creating a single point of failure.',
    resource: {
      resource_id: 'mydb',
      resource_type: 'rds:instance',
      resource_name: 'mydb',
      region: 'us-east-1',
    },
    recommendation: 'Enable Multi-AZ deployment for high availability.',
    remediation_available: true,
    detected_at: new Date().toISOString(),
  },
]

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Overview of your AWS cloud health</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
          <RefreshCw className="w-4 h-4" />
          Run Scan
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Monthly Spend"
          value="$12,450"
          subtitle="Last 30 days"
          icon={<DollarSign className="w-6 h-6" />}
          trend={{ value: -8.2, isPositive: true }}
        />
        <StatCard
          title="Potential Savings"
          value="$2,340"
          subtitle="18.8% of spend"
          icon={<TrendingDown className="w-6 h-6" />}
          variant="success"
        />
        <StatCard
          title="Security Issues"
          value="12"
          subtitle="3 critical, 5 high"
          icon={<Shield className="w-6 h-6" />}
          variant="danger"
        />
        <StatCard
          title="Total Findings"
          value="44"
          subtitle="Across all categories"
          icon={<AlertTriangle className="w-6 h-6" />}
          variant="warning"
        />
      </div>

      {/* Scores & Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scores */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Health Scores</h2>
          <div className="flex justify-around">
            <ScoreGauge score={72} label="Security" />
            <ScoreGauge score={85} label="Reliability" />
            <ScoreGauge score={68} label="Cost Efficiency" />
          </div>
        </div>

        {/* Cost Trend */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Cost Trend (30 days)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={costTrend}>
                <defs>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(v) => `$${v / 1000}k`} />
                <Tooltip
                  formatter={(value: number) => [`$${value.toLocaleString()}`, 'Cost']}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke="#6366F1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorCost)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Findings Distribution & Top Issues */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Findings by Category */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Findings by Category</h2>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={findingsByCategory}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {findingsByCategory.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4">
            {findingsByCategory.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-gray-600">
                  {item.name} ({item.value})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Findings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Top Priority Findings</h2>
            <a href="/findings" className="text-sm text-primary-600 hover:text-primary-700">
              View all →
            </a>
          </div>
          <div className="space-y-3">
            {topFindings.map((finding) => (
              <FindingCard
                key={finding.finding_id}
                finding={finding}
                onRemediate={(id) => console.log('Remediate:', id)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">156</div>
          <div className="text-sm text-gray-500">Resources Scanned</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-green-600">23</div>
          <div className="text-sm text-gray-500">Issues Fixed (30d)</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-primary-600">$4,520</div>
          <div className="text-sm text-gray-500">Savings Realized</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">3</div>
          <div className="text-sm text-gray-500">AWS Regions</div>
        </div>
      </div>
    </div>
  )
}
