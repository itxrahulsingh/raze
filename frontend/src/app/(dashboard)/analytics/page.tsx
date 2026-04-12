'use client'
import { useEffect, useState } from 'react'

export default function AnalyticsPage() {
  const [overview, setOverview] = useState({
    today_requests: 0,
    week_requests: 0,
    total_cost_usd: 0
  })

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/analytics/overview', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setOverview(await res.json())
    } catch (e) {
      console.error('Failed to fetch analytics')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Analytics</h1>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Today Requests</p>
          <p className="text-3xl font-bold">{overview.today_requests}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">This Week Requests</p>
          <p className="text-3xl font-bold">{overview.week_requests}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600">Total Cost (USD)</p>
          <p className="text-3xl font-bold">${overview.total_cost_usd.toFixed(2)}</p>
        </div>
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">AI Decision Logs</h2>
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  )
}
