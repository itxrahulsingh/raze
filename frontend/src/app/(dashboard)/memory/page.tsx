'use client'

import { useEffect, useMemo, useState } from 'react'
import { Brain, Gauge, Layers3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface MemoryItem {
  id: string
  type?: string
  content?: string
  importance_score?: number
  is_active?: boolean
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMemories()
  }, [])

  const fetchMemories = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/memory?user_id=user-001', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMemories(Array.isArray(data) ? data : data.items || [])
      }
    } catch {
      // keep stable fallback
    } finally {
      setLoading(false)
    }
  }

  const metrics = useMemo(() => {
    const total = memories.length
    const active = memories.filter((m) => m.is_active).length
    const avgImportance =
      total === 0
        ? 0
        : memories.reduce((acc, m) => acc + (m.importance_score || 0), 0) / total
    return { total, active, avgImportance }
  }, [memories])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Memory</p>
        <h2 className="mt-2 text-3xl font-display font-semibold">Memory Management</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Inspect persistence quality, activation status, and memory salience for the agent runtime.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Memories</CardDescription>
            <CardTitle className="text-3xl">{metrics.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Memories</CardDescription>
            <CardTitle className="text-3xl">{metrics.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Importance</CardDescription>
            <CardTitle className="text-3xl">{(metrics.avgImportance * 100).toFixed(1)}%</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Memory Entries</CardTitle>
          <CardDescription>Current indexed memory records and strength score.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading memories...</p>
          ) : memories.length === 0 ? (
            <p className="text-sm text-muted-foreground">No memories found.</p>
          ) : (
            <div className="space-y-3">
              {memories.map((m) => {
                const score = Math.max(0, Math.min(1, m.importance_score || 0))
                return (
                  <div key={m.id} className="rounded-xl border border-border/70 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            <Layers3 className="mr-1 h-3.5 w-3.5" />
                            {m.type || 'memory'}
                          </Badge>
                          <Badge variant={m.is_active ? 'success' : 'secondary'}>
                            {m.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                          {m.content || 'No content available.'}
                        </p>
                      </div>
                      <div className="min-w-44 rounded-lg border border-border/60 p-3">
                        <p className="mb-2 flex items-center text-xs text-muted-foreground">
                          <Gauge className="mr-1.5 h-3.5 w-3.5" />
                          Importance
                        </p>
                        <div className="h-2 w-full rounded-full bg-secondary">
                          <div
                            className="h-2 rounded-full bg-primary"
                            style={{ width: `${score * 100}%` }}
                          />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{(score * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
