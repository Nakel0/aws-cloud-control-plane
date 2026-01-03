export default function Dashboard() {
  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of your AWS infrastructure health, costs, and security
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="stat-card">
          <div className="stat-value">$12,456</div>
          <div className="stat-label">Monthly AWS Spend</div>
          <div className="stat-change stat-change-negative">
            ↑ 8% from last month
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-value">$3,789</div>
          <div className="stat-label">Potential Savings</div>
          <div className="stat-change stat-change-positive">
            30.4% of total spend
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-value">23</div>
          <div className="stat-label">Critical Security Issues</div>
          <div className="stat-change stat-change-negative">
            ↑ 5 new this week
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-value">94%</div>
          <div className="stat-label">Infrastructure Health</div>
          <div className="stat-change stat-change-positive">
            ↑ 2% improvement
          </div>
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Cost by Service
          </h2>
          <div className="space-y-4">
            {[
              { name: 'EC2', cost: 4200, percent: 34 },
              { name: 'RDS', cost: 2800, percent: 22 },
              { name: 'S3', cost: 1900, percent: 15 },
              { name: 'Lambda', cost: 1400, percent: 11 },
              { name: 'Other', cost: 2156, percent: 18 },
            ].map((service) => (
              <div key={service.name}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">
                    {service.name}
                  </span>
                  <span className="text-sm font-medium text-gray-900">
                    ${service.cost.toLocaleString()}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full"
                    style={{ width: `${service.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Security Findings
          </h2>
          <div className="space-y-3">
            {[
              { severity: 'Critical', count: 23, color: 'danger' },
              { severity: 'High', count: 47, color: 'warning' },
              { severity: 'Medium', count: 89, color: 'primary' },
              { severity: 'Low', count: 156, color: 'success' },
            ].map((finding) => (
              <div
                key={finding.severity}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <span className={`badge badge-${finding.color}`}>
                    {finding.severity}
                  </span>
                </div>
                <span className="text-2xl font-bold text-gray-900">
                  {finding.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Recommendations */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Top Recommendations
        </h2>
        <div className="space-y-4">
          {[
            {
              title: 'Idle EC2 instance detected',
              description: 'i-1234567890 has been running with <5% CPU for 14 days',
              savings: 142.56,
              priority: 'high',
            },
            {
              title: 'Unattached EBS volumes',
              description: '3 volumes unattached for >30 days',
              savings: 89.40,
              priority: 'medium',
            },
            {
              title: 'Reserved Instance opportunity',
              description: 't3.medium instances running 24/7',
              savings: 423.00,
              priority: 'high',
            },
          ].map((rec, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <span
                    className={`badge badge-${
                      rec.priority === 'high' ? 'danger' : 'warning'
                    }`}
                  >
                    {rec.priority.toUpperCase()}
                  </span>
                  <h3 className="font-medium text-gray-900">{rec.title}</h3>
                </div>
                <p className="text-sm text-gray-600">{rec.description}</p>
              </div>
              <div className="text-right ml-4">
                <div className="text-lg font-bold text-success-600">
                  ${rec.savings.toFixed(2)}/mo
                </div>
                <button className="mt-2 text-sm text-primary-600 hover:text-primary-700 font-medium">
                  View Details →
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
