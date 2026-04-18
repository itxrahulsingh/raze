'use client'

import { useEffect, useState } from 'react'
import { Activity, Bot, DollarSign, Sparkles, Wrench } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

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
    total_cost_usd: 0,
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

      const overviewRes = await fetch('/api/v1/analytics/overview', { headers })
      if (overviewRes.ok) setOverview(await overviewRes.json())

      const modelsRes = await fetch('/api/v1/analytics/models', { headers })
      if (modelsRes.ok) {
        const data = await modelsRes.json()
        setModels(data.models || [])
      }

      const toolsRes = await fetch('/api/v1/analytics/tools', { headers })
      if (toolsRes.ok) {
        const data = await toolsRes.json()
        setTools(data.tools || [])
      }

      const logsRes = await fetch('/api/v1/analytics/observability?limit=10', { headers })
      if (logsRes.ok) setLogs(await logsRes.json())
    } catch {
      // keep page stable with defaults
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Analytics</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Model & Tool Intelligence</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Track request volume, routing spend, and decision-level observability in one place.
            </p>
          </div>
          <Badge variant="secondary">
            <Sparkles className="mr-1.5 h-3.5 w-3.5" />
            Live Telemetry
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Today Requests</CardDescription>
            <CardTitle className="text-3xl">{overview.today_requests.toLocaleString()}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <Activity className="mr-1 inline h-3.5 w-3.5" />
            Real-time request volume
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Weekly Requests</CardDescription>
            <CardTitle className="text-3xl">{overview.week_requests.toLocaleString()}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <Bot className="mr-1 inline h-3.5 w-3.5" />
            Aggregated across providers
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Cost</CardDescription>
            <CardTitle className="text-3xl">${overview.total_cost_usd.toFixed(2)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <DollarSign className="mr-1 inline h-3.5 w-3.5" />
            Cumulative spend (USD)
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Model Usage Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading model analytics...</p>
            ) : models.length > 0 ? (
              <div className="space-y-3">
                {models.map((model, idx) => (
                  <div key={idx} className="rounded-xl border border-border/70 p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{model.model || 'Unknown'}</p>
                        <p className="text-xs text-muted-foreground">{model.usage_count} calls</p>
                      </div>
                      <Badge variant="outline">${(model.total_cost || 0).toFixed(4)}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No model usage data available.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tool Usage Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading tool analytics...</p>
            ) : tools.length > 0 ? (
              <div className="space-y-3">
                {tools.map((tool, idx) => (
                  <div key={idx} className="rounded-xl border border-border/70 p-3">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{tool.tool || 'Unknown'}</p>
                      <Badge variant="secondary">
                        <Wrench className="mr-1 h-3.5 w-3.5" />
                        {tool.usage_count}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No tool usage data available.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent AI Decision Logs</CardTitle>
          <CardDescription>Latest routing and tool-selection outcomes.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading observability logs...</p>
          ) : logs.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Timestamp</th>
                    <th className="py-2 pr-4 font-medium">Model</th>
                    <th className="py-2 pr-4 font-medium">Tool</th>
                    <th className="py-2 font-medium">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, idx) => (
                    <tr key={idx} className="border-b border-border/60">
                      <td className="py-3 pr-4">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="py-3 pr-4">{log.model_selected || '-'}</td>
                      <td className="py-3 pr-4">{log.tool_selected || '-'}</td>
                      <td className="py-3">${(log.cost_usd || 0).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No decision logs available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
