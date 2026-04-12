'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push('/login')
    } else {
      fetchUser(token)
    }
  }, [router])

  const fetchUser = async (token: string) => {
    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setUser(await res.json())
    } catch (e) {
      console.error('Failed to fetch user')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    router.push('/login')
  }

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    { name: 'Knowledge', href: '/knowledge', icon: '📚' },
    { name: 'Conversations', href: '/conversations', icon: '💬' },
    { name: 'Memory', href: '/memory', icon: '🧠' },
    { name: 'Tools', href: '/tools', icon: '🔧' },
    { name: 'Analytics', href: '/analytics', icon: '📈' },
    { name: 'Users', href: '/users', icon: '👥' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex">
        {/* Sidebar */}
        <div className="w-64 bg-slate-900 text-white min-h-screen p-4">
          <h1 className="text-2xl font-bold mb-8">RAZE</h1>
          <nav className="space-y-2">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="block px-4 py-2 rounded hover:bg-slate-800 transition"
              >
                {item.icon} {item.name}
              </a>
            ))}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          {/* Top Bar */}
          <div className="bg-white shadow-sm p-4 flex justify-between items-center">
            <h2 className="text-xl font-bold">{user?.email || 'Admin'}</h2>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              Logout
            </button>
          </div>

          {/* Page Content */}
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
