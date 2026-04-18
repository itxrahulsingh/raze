'use client'
import { useAuth } from '@/lib/auth-context'
import { useEffect, useState } from 'react'

export function TokenExpiryWarning() {
  const { isTokenExpiring, refreshToken, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    setIsOpen(isTokenExpiring)
  }, [isTokenExpiring])

  if (!isOpen) return null

  return (
    <div className="fixed top-0 right-0 left-0 z-50 bg-yellow-50 border-b border-yellow-200 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">⏰</div>
            <div>
              <p className="font-semibold text-yellow-900">Session expiring soon</p>
              <p className="text-sm text-yellow-700">Your session will expire in 5 minutes. Please save your work.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                refreshToken().then(() => setIsOpen(false))
              }}
              className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm font-medium"
            >
              Refresh Session
            </button>
            <button
              onClick={() => logout()}
              className="px-4 py-2 bg-gray-200 text-gray-900 rounded hover:bg-gray-300 text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
