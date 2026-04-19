'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, RefreshCcw, Search, ShieldCheck, Wrench } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface ToolItem {
  id: string
  name: string
  display_name?: string | null
  description?: string
  type?: string
  usage_count?: number
  success_rate?: number
  avg_latency_ms?: number
  last_used?: string | null
  is_active?: boolean
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const fetchTools = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/tools?limit=200', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to load tools (${res.status})`)
      const data = await res.json()
      setTools(Array.isArray(data) ? data : data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools')
      setTools([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTools()
  }, [fetchTools])

  const filteredTools = useMemo(
    () =>
      tools.filter((tool) =>
        `${tool.name} ${tool.display_name || ''} ${tool.description || ''}`
          .toLowerCase()
          .includes(query.toLowerCase())
      ),
    [query, tools]
  )

  const summary = useMemo(() => {
    const total = filteredTools.length
    const totalUsage = filteredTools.reduce((acc, tool) => acc + (tool.usage_count || 0), 0)
    const avgSuccess =
      total === 0
        ? 0
        : filteredTools.reduce((acc, tool) => acc + ((tool.success_rate || 0) * 100), 0) / total
    return { total, totalUsage, avgSuccess }
  }, [filteredTools])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Tooling</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Tool Management Grid</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Track operational health, execution volume, and runtime reliability of connected tools.
            </p>
          </div>
          <Button variant="outline" onClick={fetchTools} disabled={loading}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Tools</CardDescription>
            <CardTitle className="text-3xl">{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Executions</CardDescription>
            <CardTitle className="text-3xl">{summary.totalUsage.toLocaleString()}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Average Success</CardDescription>
            <CardTitle className="text-3xl">{summary.avgSuccess.toFixed(1)}%</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registered Tools</CardTitle>
          <CardDescription>Operational status and utilization details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search tools..."
            />
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading tools...</p>
          ) : filteredTools.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tools match the current filter.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredTools.map((tool) => (
                <div key={tool.id} className="rounded-xl border border-border/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{tool.display_name || tool.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {tool.description || 'No description provided.'}
                      </p>
                    </div>
                    <div className="rounded-lg bg-secondary p-2">
                      <Wrench className="h-4 w-4 text-primary" />
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="outline">{tool.type || 'custom'}</Badge>
                    <Badge variant="secondary">
                      <Activity className="mr-1 h-3.5 w-3.5" />
                      {tool.usage_count || 0}
                    </Badge>
                    <Badge variant={(tool.success_rate || 0) >= 0.8 ? 'success' : 'warning'}>
                      <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                      {((tool.success_rate || 0) * 100).toFixed(1)}%
                    </Badge>
                  </div>

                  <div className="mt-3 text-xs text-muted-foreground">
                    <p>Avg latency: {Math.round(tool.avg_latency_ms || 0)}ms</p>
                    <p>
                      Last used:{' '}
                      {tool.last_used ? new Date(tool.last_used).toLocaleString() : 'Never'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
