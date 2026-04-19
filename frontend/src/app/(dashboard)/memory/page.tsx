'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Brain, Gauge, Layers3, RefreshCcw, Search } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

interface MemoryItem {
  id: string
  type?: string
  content?: string
  importance_score?: number
  is_active?: boolean
  created_at?: string
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')

  const fetchMemories = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('access_token')
      const params = new URLSearchParams()
      params.set('limit', '100')
      if (typeFilter !== 'all') params.set('memory_type', typeFilter)
      const res = await fetch(`/api/v1/memory?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to load memories (${res.status})`)
      const data = await res.json()
      setMemories(Array.isArray(data) ? data : data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memories')
      setMemories([])
    } finally {
      setLoading(false)
    }
  }, [typeFilter])

  useEffect(() => {
    fetchMemories()
  }, [fetchMemories])

  const filteredMemories = useMemo(
    () =>
      memories.filter((memory) =>
        `${memory.type || ''} ${memory.content || ''}`.toLowerCase().includes(query.toLowerCase())
      ),
    [memories, query]
  )

  const metrics = useMemo(() => {
    const total = filteredMemories.length
    const active = filteredMemories.filter((memory) => memory.is_active).length
    const avgImportance =
      total === 0
        ? 0
        : filteredMemories.reduce((acc, memory) => acc + (memory.importance_score || 0), 0) / total
    return { total, active, avgImportance }
  }, [filteredMemories])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Memory</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Memory Management</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Inspect persistent context quality, activation status, and salience of agent memories.
            </p>
          </div>
          <Button variant="outline" onClick={fetchMemories} disabled={loading}>
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
          <CardDescription>Indexed memory records and retention signal strength.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_220px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search memory content..."
              />
            </div>
            <Select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value || 'all')}>
              <option value="all">All types</option>
              <option value="context">Context</option>
              <option value="user">User</option>
              <option value="operational">Operational</option>
              <option value="knowledge">Knowledge</option>
            </Select>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading memories...</p>
          ) : filteredMemories.length === 0 ? (
            <p className="text-sm text-muted-foreground">No memories found for current filter.</p>
          ) : (
            <div className="space-y-3">
              {filteredMemories.map((memory) => {
                const score = Math.max(0, Math.min(1, memory.importance_score || 0))
                return (
                  <div key={memory.id} className="rounded-xl border border-border/70 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            <Layers3 className="mr-1 h-3.5 w-3.5" />
                            {memory.type || 'memory'}
                          </Badge>
                          <Badge variant={memory.is_active ? 'success' : 'secondary'}>
                            {memory.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{memory.content || 'No content available.'}</p>
                        <p className="mt-2 text-xs text-muted-foreground">
                          Created: {memory.created_at ? new Date(memory.created_at).toLocaleString() : 'Unknown'}
                        </p>
                      </div>
                      <div className="min-w-44 rounded-lg border border-border/60 p-3">
                        <p className="mb-2 flex items-center text-xs text-muted-foreground">
                          <Gauge className="mr-1.5 h-3.5 w-3.5" />
                          Importance
                        </p>
                        <div className="h-2 w-full rounded-full bg-secondary">
                          <div className="h-2 rounded-full bg-primary" style={{ width: `${score * 100}%` }} />
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            Memory Notes
          </CardTitle>
          <CardDescription>
            Memory listing is scoped to the logged-in user by backend policy.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
