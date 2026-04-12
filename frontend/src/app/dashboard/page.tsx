'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [stats, setStats] = useState({
    conversations: 0,
    messages: 0,
    sources: 0
  })

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push('/login')
      return
    }
    fetchDashboard(token)
  }, [router])

  const fetchDashboard = async (token: string) => {
    try {
      const [userRes, dashRes] = await Promise.all([
        fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/admin/dashboard', { headers: { Authorization: `Bearer ${token}` } })
      ])

      if (userRes.ok) setUser(await userRes.json())
      if (dashRes.ok) setStats(await dashRes.json())
    } catch (err) {
      console.error('Failed to fetch dashboard', err)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between">
          <h1 className="text-2xl font-bold">RAZE Admin</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.email}</span>
            <button onClick={handleLogout} className="bg-red-600 text-white px-4 py-2 rounded">
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-4">
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-600 text-sm">Conversations</h3>
            <p className="text-3xl font-bold">{stats.conversations}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-600 text-sm">Messages</h3>
            <p className="text-3xl font-bold">{stats.messages}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-gray-600 text-sm">Knowledge Sources</h3>
            <p className="text-3xl font-bold">{stats.sources}</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4">System Status</h2>
          <div className="space-y-2 text-sm">
            <p><span className="text-green-600">●</span> Database: Healthy</p>
            <p><span className="text-green-600">●</span> Cache: Healthy</p>
            <p><span className="text-green-600">●</span> Vector Search: Healthy</p>
          </div>
        </div>
      </div>
    </div>
  )
}
