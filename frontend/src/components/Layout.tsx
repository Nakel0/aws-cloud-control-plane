import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', path: '/', icon: '📊' },
    { name: 'Cost Analysis', path: '/cost', icon: '💰' },
    { name: 'Security', path: '/security', icon: '🔒' },
    { name: 'Recommendations', path: '/recommendations', icon: '💡' },
  ]

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === path
    }
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-primary-600">
                ☁️ CloudGuard
              </h1>
              <span className="ml-3 text-sm text-gray-500">
                AWS Optimization Platform
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <button className="text-gray-600 hover:text-gray-900">
                🔔
              </button>
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-medium">
                  U
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {navigation.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center space-x-2 px-3 py-4 text-sm font-medium border-b-2 transition-colors
                  ${
                    isActive(item.path)
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{item.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">
              © 2026 CloudGuard. All rights reserved.
            </p>
            <div className="flex space-x-6">
              <a href="#" className="text-sm text-gray-500 hover:text-gray-900">
                Documentation
              </a>
              <a href="#" className="text-sm text-gray-500 hover:text-gray-900">
                Support
              </a>
              <a href="#" className="text-sm text-gray-500 hover:text-gray-900">
                API
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
