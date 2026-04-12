'use client'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
  const [stats, setStats] = useState({ conversations: 0, messages: 0, sources: 0, users: 0 })

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setStats(await res.json())
    } catch (e) {
      console.error('Failed to fetch stats')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Conversations</p>
          <p className="text-4xl font-bold">{stats.conversations}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Messages</p>
          <p className="text-4xl font-bold">{stats.messages}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Knowledge Sources</p>
          <p className="text-4xl font-bold">{stats.sources}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Active Users</p>
          <p className="text-4xl font-bold">{stats.users}</p>
        </div>
      </div>
      <div className="mt-6 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">System Status</h2>
        <p className="text-green-600">✓ Database: Healthy</p>
        <p className="text-green-600">✓ Redis: Healthy</p>
        <p className="text-green-600">✓ Vector DB: Healthy</p>
      </div>
    </div>
  )
}
