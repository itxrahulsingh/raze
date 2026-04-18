'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { SettingsProvider, useSettings } from '@/lib/settings-context'

function DashboardLayoutContent({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const { whiteLabelSettings } = useSettings()

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
    { name: 'Admin Chat', href: '/admin-chat', icon: '🤖' },
    { name: 'Chat SDK', href: '/chat-sdk', icon: '💻' },
    { name: 'Conversations', href: '/conversations', icon: '💬' },
    { name: 'Memory', href: '/memory', icon: '🧠' },
    { name: 'Tools', href: '/tools', icon: '🔧' },
    { name: 'Analytics', href: '/analytics', icon: '📈' },
    { name: 'Users', href: '/users', icon: '👥' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ]

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f8fafc' }}>
      <style>{`
        :root {
          --brand-color: ${whiteLabelSettings.brand_color};
        }
        .brand-sidebar { background-color: #1e293b; }
        .brand-accent { color: var(--brand-color); }
        .brand-bg { background-color: var(--brand-color); }
        .brand-hover:hover { background-color: var(--brand-color); }
      `}</style>
      
      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-64 brand-sidebar text-white min-h-screen p-6 flex flex-col overflow-y-auto shadow-lg">
          {/* Brand Logo & Name */}
          <div className="mb-8 pb-6 border-b border-slate-700">
            <div className="flex items-center gap-3">
              {whiteLabelSettings.logo_url && (
                <img 
                  src={whiteLabelSettings.logo_url} 
                  alt="Logo" 
                  className="w-10 h-10 rounded"
                />
              )}
              <div>
                <h1 className="text-xl font-bold">{whiteLabelSettings.brand_name}</h1>
                <p className="text-xs text-slate-400">Enterprise AI OS</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="block px-4 py-3 rounded-lg hover:bg-slate-800 transition duration-200 text-sm font-medium"
              >
                <span className="text-lg mr-2">{item.icon}</span>
                {item.name}
              </a>
            ))}
          </nav>

          {/* Logout */}
          <div className="pt-4 border-t border-slate-700">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition text-sm font-medium"
            >
              🚪 Logout
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <div className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm flex justify-between items-center">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-slate-600">Logged in as</h2>
              <p className="text-lg font-bold text-slate-900">{user?.email || 'Admin'}</p>
            </div>
            <div className="flex items-center gap-4">
              <a href="/settings" className="text-slate-600 hover:text-slate-900 text-sm font-medium">
                ⚙️ Settings
              </a>
            </div>
          </div>

          {/* Page Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SettingsProvider>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </SettingsProvider>
  )
}
