import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  DollarSign, 
  Shield, 
  Activity, 
  AlertTriangle,
  Cloud,
  Settings,
  RefreshCw
} from 'lucide-react'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Cost Optimization', href: '/cost', icon: DollarSign },
  { name: 'Security', href: '/security', icon: Shield },
  { name: 'Reliability', href: '/reliability', icon: Activity },
  { name: 'All Findings', href: '/findings', icon: AlertTriangle },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-200">
          <div className="p-2 bg-primary-600 rounded-lg">
            <Cloud className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">CloudGuard</h1>
            <p className="text-xs text-gray-500">AWS Optimization</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="px-3 py-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <item.icon className={clsx('w-5 h-5', isActive ? 'text-primary-600' : 'text-gray-400')} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <RefreshCw className="w-4 h-4" />
            <span>Last scan: Just now</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
