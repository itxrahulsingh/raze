'use client'
import { useEffect, useState } from 'react'

interface Model {
  model: string
  usage_count: number
  total_cost: number
}

interface Tool {
  tool: string
  usage_count: number
}

interface Log {
  created_at: string
  model_selected: string
  tool_selected: string
  cost_usd: number
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState({
    today_requests: 0,
    week_requests: 0,
    total_cost_usd: 0
  })
  const [models, setModels] = useState<Model[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [logs, setLogs] = useState<Log[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAllAnalytics()
  }, [])

  const fetchAllAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const headers = { Authorization: `Bearer ${token}` }

      // Fetch overview
      const overviewRes = await fetch('/api/v1/analytics/overview', { headers })
      if (overviewRes.ok) setOverview(await overviewRes.json())

      // Fetch model usage
      const modelsRes = await fetch('/api/v1/analytics/models', { headers })
      if (modelsRes.ok) {
        const data = await modelsRes.json()
        setModels(data.models || [])
      }

      // Fetch tool usage
      const toolsRes = await fetch('/api/v1/analytics/tools', { headers })
      if (toolsRes.ok) {
        const data = await toolsRes.json()
        setTools(data.tools || [])
      }

      // Fetch observability logs
      const logsRes = await fetch('/api/v1/analytics/observability?limit=10', { headers })
      if (logsRes.ok) setLogs(await logsRes.json())
    } catch (e) {
      console.error('Failed to fetch analytics:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Analytics Dashboard</h1>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm font-medium">Today Requests</p>
          <p className="text-3xl font-bold mt-2">{overview.today_requests}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm font-medium">This Week Requests</p>
          <p className="text-3xl font-bold mt-2">{overview.week_requests}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-gray-600 text-sm font-medium">Total Cost (USD)</p>
          <p className="text-3xl font-bold mt-2">${overview.total_cost_usd.toFixed(2)}</p>
        </div>
      </div>

      {/* Model Usage */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Model Usage Breakdown</h2>
        {loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : models.length > 0 ? (
          <div className="space-y-3">
            {models.map((model, idx) => (
              <div key={idx} className="flex justify-between items-center border-b pb-3">
                <div>
                  <p className="font-medium">{model.model || 'Unknown'}</p>
                  <p className="text-sm text-gray-600">Usage: {model.usage_count} calls</p>
                </div>
                <p className="font-bold">${(model.total_cost || 0).toFixed(4)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-600">No model usage data available</p>
        )}
      </div>

      {/* Tool Usage */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Tool Usage Statistics</h2>
        {loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : tools.length > 0 ? (
          <div className="space-y-3">
            {tools.map((tool, idx) => (
              <div key={idx} className="flex justify-between items-center border-b pb-3">
                <p className="font-medium">{tool.tool || 'Unknown'}</p>
                <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                  {tool.usage_count} calls
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-600">No tool usage data available</p>
        )}
      </div>

      {/* AI Decision Logs */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Recent AI Decision Logs</h2>
        {loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr>
                  <th className="text-left py-2">Timestamp</th>
                  <th className="text-left py-2">Model</th>
                  <th className="text-left py-2">Tool</th>
                  <th className="text-left py-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-3">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="py-3">{log.model_selected || '-'}</td>
                    <td className="py-3">{log.tool_selected || '-'}</td>
                    <td className="py-3">${(log.cost_usd || 0).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-600">No decision logs available</p>
        )}
      </div>
    </div>
  )
}
