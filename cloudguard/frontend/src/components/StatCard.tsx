import { ReactNode } from 'react'
import clsx from 'clsx'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  variant?: 'default' | 'success' | 'warning' | 'danger'
}

const variantStyles = {
  default: 'bg-white',
  success: 'bg-green-50 border-green-100',
  warning: 'bg-yellow-50 border-yellow-100',
  danger: 'bg-red-50 border-red-100',
}

const iconVariantStyles = {
  default: 'bg-primary-100 text-primary-600',
  success: 'bg-green-100 text-green-600',
  warning: 'bg-yellow-100 text-yellow-600',
  danger: 'bg-red-100 text-red-600',
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = 'default',
}: StatCardProps) {
  return (
    <div
      className={clsx(
        'rounded-xl border p-6 card-hover',
        variantStyles[variant]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500">{subtitle}</p>
          )}
          {trend && (
            <div className="flex items-center gap-1">
              <span
                className={clsx(
                  'text-sm font-medium',
                  trend.isPositive ? 'text-green-600' : 'text-red-600'
                )}
              >
                {trend.isPositive ? '+' : ''}{trend.value}%
              </span>
              <span className="text-sm text-gray-500">vs last month</span>
            </div>
          )}
        </div>
        <div
          className={clsx(
            'p-3 rounded-lg',
            iconVariantStyles[variant]
          )}
        >
          {icon}
        </div>
      </div>
    </div>
  )
}
