import clsx from 'clsx'

interface ScoreGaugeProps {
  score: number
  label: string
  size?: 'sm' | 'md' | 'lg'
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-500'
  if (score >= 60) return 'text-yellow-500'
  if (score >= 40) return 'text-orange-500'
  return 'text-red-500'
}

function getScoreBackground(score: number): string {
  if (score >= 80) return 'bg-green-100'
  if (score >= 60) return 'bg-yellow-100'
  if (score >= 40) return 'bg-orange-100'
  return 'bg-red-100'
}

function getScoreStroke(score: number): string {
  if (score >= 80) return 'stroke-green-500'
  if (score >= 60) return 'stroke-yellow-500'
  if (score >= 40) return 'stroke-orange-500'
  return 'stroke-red-500'
}

const sizeConfig = {
  sm: { width: 80, strokeWidth: 6, fontSize: 'text-lg' },
  md: { width: 120, strokeWidth: 8, fontSize: 'text-2xl' },
  lg: { width: 160, strokeWidth: 10, fontSize: 'text-4xl' },
}

export default function ScoreGauge({ score, label, size = 'md' }: ScoreGaugeProps) {
  const config = sizeConfig[size]
  const radius = (config.width - config.strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDashoffset = circumference - (score / 100) * circumference

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: config.width, height: config.width }}>
        {/* Background circle */}
        <svg
          className="absolute inset-0 -rotate-90"
          width={config.width}
          height={config.width}
        >
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            strokeWidth={config.strokeWidth}
            className="stroke-gray-200"
          />
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            strokeWidth={config.strokeWidth}
            strokeLinecap="round"
            className={clsx('transition-all duration-1000', getScoreStroke(score))}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset,
            }}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={clsx('font-bold', config.fontSize, getScoreColor(score))}>
            {score}
          </span>
        </div>
      </div>
      <p className="mt-2 text-sm font-medium text-gray-600">{label}</p>
    </div>
  )
}
