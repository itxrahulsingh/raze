'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, Bot, DollarSign, RefreshCcw, Sparkles, Wrench } from 'lucide-react'

import { useAuth } from '@/lib/auth-context'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

interface ModelUsage {
  model: string
  usage_count: number
  total_cost: number
}

interface ToolUsage {
  tool: string
  usage_count: number
}

interface ObservabilityLog {
  id?: string
  created_at: string
  model_selected?: string | null
  tool_selected?: string | null
  cost_usd?: number | null
}

interface Overview {
  today_requests: number
  week_requests: number
  month_requests?: number
  total_cost_usd: number
}

export default function AnalyticsPage() {
  const { token, isAuthenticated } = useAuth()
  const [overview, setOverview] = useState<Overview>({
    today_requests: 0,
    week_requests: 0,
    month_requests: 0,
    total_cost_usd: 0,
  })
  const [models, setModels] = useState<ModelUsage[]>([])
  const [tools, setTools] = useState<ToolUsage[]>([])
  const [logs, setLogs] = useState<ObservabilityLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const getToken = useCallback(() => token || localStorage.getItem('access_token'), [token])

  const safeNumber = (value: unknown, fallback = 0) => {
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string') {
      const parsed = Number(value)
      return Number.isFinite(parsed) ? parsed : fallback
    }
    return fallback
  }

  const fetchAllAnalytics = useCallback(async () => {
    const authToken = getToken()
    if (!authToken) return

    setLoading(true)
    setError(null)

    const headers = { Authorization: `Bearer ${authToken}` }

    try {
      const [overviewRes, modelsRes, toolsRes, logsRes] = await Promise.allSettled([
        fetch('/api/v1/analytics/overview', { headers }),
        fetch('/api/v1/analytics/models', { headers }),
        fetch('/api/v1/analytics/tools', { headers }),
        fetch('/api/v1/analytics/observability?limit=20', { headers }),
      ])

      if (overviewRes.status === 'fulfilled' && overviewRes.value.ok) {
        const payload = await overviewRes.value.json()
        setOverview({
          today_requests: safeNumber(payload.today_requests),
          week_requests: safeNumber(payload.week_requests),
          month_requests: safeNumber(payload.month_requests),
          total_cost_usd: safeNumber(payload.total_cost_usd),
        })
      }

      if (modelsRes.status === 'fulfilled' && modelsRes.value.ok) {
        const payload = await modelsRes.value.json()
        setModels((payload.models || []).map((item: any) => ({
          model: item.model || 'unknown',
          usage_count: safeNumber(item.usage_count),
          total_cost: safeNumber(item.total_cost),
        })))
      }

      if (toolsRes.status === 'fulfilled' && toolsRes.value.ok) {
        const payload = await toolsRes.value.json()
        setTools((payload.tools || []).map((item: any) => ({
          tool: item.tool || 'unknown',
          usage_count: safeNumber(item.usage_count),
        })))
      }

      if (logsRes.status === 'fulfilled' && logsRes.value.ok) {
        const payload = await logsRes.value.json()
        const entries = Array.isArray(payload) ? payload : payload.items || []
        setLogs(
          entries.map((entry: any) => ({
            id: entry.id,
            created_at: entry.created_at,
            model_selected: entry.model_selected,
            tool_selected: entry.tool_selected,
            cost_usd: safeNumber(entry.cost_usd, 0),
          }))
        )
      }
    } catch {
      setError('Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    if (!isAuthenticated) return
    fetchAllAnalytics()
  }, [fetchAllAnalytics, isAuthenticated])

  const topModel = useMemo(() => {
    if (models.length === 0) return 'N/A'
    return [...models].sort((a, b) => b.usage_count - a.usage_count)[0].model
  }, [models])

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Analytics</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Model & Tool Intelligence</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Track request volume, routing spend, model distribution, and decision-level observability.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Live Telemetry
            </Badge>
            <Button variant="outline" onClick={fetchAllAnalytics} disabled={loading}>
              <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
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

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Top Model</CardDescription>
            <CardTitle className="text-xl">{topModel}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">
            <Bot className="mr-1 inline h-3.5 w-3.5" />
            Highest request share
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
                {models.map((entry) => (
                  <div key={`${entry.model}-${entry.usage_count}`} className="rounded-xl border border-border/70 p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{entry.model}</p>
                        <p className="text-xs text-muted-foreground">{entry.usage_count} calls</p>
                      </div>
                      <Badge variant="outline">${entry.total_cost.toFixed(4)}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No model usage data available yet.</p>
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
                {tools.map((entry) => (
                  <div key={`${entry.tool}-${entry.usage_count}`} className="rounded-xl border border-border/70 p-3">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{entry.tool}</p>
                      <Badge variant="secondary">
                        <Wrench className="mr-1 h-3.5 w-3.5" />
                        {entry.usage_count}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No tool usage data available yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent AI Decision Logs</CardTitle>
          <CardDescription>Latest model routing and tool-selection outcomes.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading observability logs...</p>
          ) : logs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Tool</TableHead>
                  <TableHead>Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((entry, idx) => (
                  <TableRow key={entry.id || `${entry.created_at}-${idx}`}>
                    <TableCell>{entry.created_at ? new Date(entry.created_at).toLocaleString() : '-'}</TableCell>
                    <TableCell>{entry.model_selected || '-'}</TableCell>
                    <TableCell>{entry.tool_selected || '-'}</TableCell>
                    <TableCell>${(entry.cost_usd || 0).toFixed(4)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No decision logs available yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
