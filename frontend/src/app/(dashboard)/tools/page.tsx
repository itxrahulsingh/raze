'use client'

import { useEffect, useMemo, useState } from 'react'
import { Wrench, Activity, ShieldCheck, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ToolItem {
  id: string
  name: string
  description?: string
  type?: string
  usage_count?: number
  success_rate?: number
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTools()
  }, [])

  const fetchTools = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/tools', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setTools(Array.isArray(data) ? data : data.items || [])
      }
    } catch {
      // keep stable fallback
    } finally {
      setLoading(false)
    }
  }

  const summary = useMemo(() => {
    const total = tools.length
    const totalUsage = tools.reduce((acc, t) => acc + (t.usage_count || 0), 0)
    const avgSuccess =
      total === 0
        ? 0
        : tools.reduce((acc, t) => acc + ((t.success_rate || 0) * 100), 0) / total

    return { total, totalUsage, avgSuccess }
  }, [tools])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Tooling</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Tool Management Grid</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Observe usage patterns, maintain reliability, and track performance of connected tools.
            </p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Tool
          </Button>
        </div>
      </div>

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
          <CardDescription>Operational status and live utilization.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading tools...</p>
          ) : tools.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tools created yet.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {tools.map((tool) => (
                <div key={tool.id} className="rounded-xl border border-border/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{tool.name}</p>
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
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
