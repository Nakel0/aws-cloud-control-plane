import { AlertTriangle, DollarSign, Shield, Activity, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import type { Finding } from '../services/api'

interface FindingCardProps {
  finding: Finding
  onRemediate?: (findingId: string) => void
}

const severityStyles = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
  info: 'bg-gray-100 text-gray-800 border-gray-200',
}

const categoryIcons = {
  cost: DollarSign,
  security: Shield,
  reliability: Activity,
}

const categoryColors = {
  cost: 'text-green-600 bg-green-100',
  security: 'text-red-600 bg-red-100',
  reliability: 'text-blue-600 bg-blue-100',
}

export default function FindingCard({ finding, onRemediate }: FindingCardProps) {
  const CategoryIcon = categoryIcons[finding.category]

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        {/* Category Icon */}
        <div className={clsx('p-2 rounded-lg', categoryColors[finding.category])}>
          <CategoryIcon className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-gray-900 truncate">{finding.title}</h3>
            <span
              className={clsx(
                'px-2 py-0.5 text-xs font-medium rounded-full border',
                severityStyles[finding.severity]
              )}
            >
              {finding.severity}
            </span>
          </div>
          
          <p className="text-sm text-gray-500 mb-2 line-clamp-2">
            {finding.description}
          </p>

          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>{finding.resource.resource_type}</span>
            <span>{finding.resource.region}</span>
            {finding.estimated_savings && (
              <span className="text-green-600 font-medium">
                Save ${finding.estimated_savings.toFixed(2)}/mo
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {finding.remediation_available && onRemediate && (
            <button
              onClick={() => onRemediate(finding.finding_id)}
              className="px-3 py-1.5 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
            >
              Fix
            </button>
          )}
          <ChevronRight className="w-5 h-5 text-gray-300" />
        </div>
      </div>
    </div>
  )
}
