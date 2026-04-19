'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Brain, Gauge, Layers3, RefreshCcw, Search, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface MemoryItem {
  id: string
  type?: string
  content?: string
  importance_score?: number
  is_active?: boolean
  created_at?: string
}

interface RetentionPolicy {
  id: string
  name: string
  type: string
  max_count: number
  ttl_days: number
  min_importance: number
}

export default function MemoryPage() {
  const [activeTab, setActiveTab] = useState('memories')
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [searchResults, setSearchResults] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [sessionId, setSessionId] = useState('')
  const [clearingSession, setClearingSession] = useState(false)
  const [policies, setPolicies] = useState<RetentionPolicy[]>([])
  const [loadingPolicies, setLoadingPolicies] = useState(false)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const token = useMemo(() => localStorage.getItem('access_token') || '', [])

  const fetchMemories = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
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
  }, [typeFilter, token])

  const semanticSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    setSearching(true)
    try {
      const res = await fetch('/api/v1/memory/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 50,
          types: typeFilter !== 'all' ? [typeFilter] : undefined,
        }),
      })
      if (!res.ok) throw new Error('Semantic search failed')
      const data = await res.json()
      setSearchResults(data.results || [])
    } catch (err) {
      console.error('Search error:', err)
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [token, typeFilter])

  const handleSearch = useCallback((value: string) => {
    setQuery(value)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(() => {
      semanticSearch(value)
    }, 300)
  }, [semanticSearch])

  const deleteMemory = useCallback(async (memoryId: string) => {
    if (!window.confirm('Delete this memory?')) return
    try {
      const res = await fetch(`/api/v1/memory/${memoryId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to delete memory')
      setMemories(prev => prev.filter(m => m.id !== memoryId))
      setSearchResults(prev => prev.filter(m => m.id !== memoryId))
      toast.success('Memory deleted')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete memory')
    }
  }, [token])

  const clearSessionContext = useCallback(async () => {
    if (!sessionId.trim()) {
      toast.error('Enter session ID')
      return
    }
    if (!window.confirm('Clear session context?')) return
    setClearingSession(true)
    try {
      const res = await fetch(`/api/v1/memory/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to clear session')
      setSessionId('')
      await fetchMemories()
      toast.success('Session cleared')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to clear session')
    } finally {
      setClearingSession(false)
    }
  }, [sessionId, token, fetchMemories])

  const fetchPolicies = useCallback(async () => {
    setLoadingPolicies(true)
    try {
      const res = await fetch('/api/v1/memory/retention-policies', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to load policies')
      const data = await res.json()
      setPolicies(data.policies || [])
    } catch (err) {
      console.error('Policy fetch error:', err)
      setPolicies([])
    } finally {
      setLoadingPolicies(false)
    }
  }, [token])

  useEffect(() => {
    fetchMemories()
    fetchPolicies()
  }, [fetchMemories, fetchPolicies])

  const displayedMemories = useMemo(() => {
    return query.trim() ? searchResults : memories
  }, [query, searchResults, memories])

  const typeBreakdown = useMemo(() => {
    const breakdown: Record<string, number> = {}
    memories.forEach(m => {
      const type = m.type || 'other'
      breakdown[type] = (breakdown[type] || 0) + 1
    })
    return breakdown
  }, [memories])

  const metrics = useMemo(() => {
    const total = displayedMemories.length
    const active = displayedMemories.filter((memory) => memory.is_active).length
    const avgImportance =
      total === 0
        ? 0
        : displayedMemories.reduce((acc, memory) => acc + (memory.importance_score || 0), 0) / total
    return { total, active, avgImportance }
  }, [displayedMemories])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Memory</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Memory Management</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Manage memories, semantic search, session context, and retention policies.
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

      {/* Stats by Type */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Memories</CardDescription>
            <CardTitle className="text-3xl">{metrics.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl">{metrics.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Importance</CardDescription>
            <CardTitle className="text-3xl">{(metrics.avgImportance * 100).toFixed(1)}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>By Type</CardDescription>
            <div className="mt-2 flex flex-wrap gap-1">
              {Object.entries(typeBreakdown).map(([type, count]) => (
                <Badge key={type} variant="outline" className="text-xs">
                  {type}: {count}
                </Badge>
              ))}
            </div>
          </CardHeader>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0">
          <TabsTrigger value="memories">Memory Entries</TabsTrigger>
          <TabsTrigger value="session">Session Context</TabsTrigger>
          <TabsTrigger value="policies">Retention Policies</TabsTrigger>
        </TabsList>

        <TabsContent value="memories">
          <Card>
            <CardHeader>
              <CardTitle>Memory Entries</CardTitle>
              <CardDescription>Search semantically or browse all memories with delete option.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-[1fr_220px]">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    value={query}
                    onChange={(event) => handleSearch(event.target.value)}
                    placeholder="Search memories semantically..."
                  />
                  {searching && <p className="text-xs text-muted-foreground mt-1">Searching...</p>}
                </div>
                <Select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value || 'all')}>
                  <option value="all">All types</option>
                  <option value="context">Context</option>
                  <option value="user">User</option>
                  <option value="operational">Operational</option>
                  <option value="knowledge">Knowledge</option>
                </Select>
              </div>

              {loading && !displayedMemories.length ? (
                <p className="text-sm text-muted-foreground">Loading memories...</p>
              ) : displayedMemories.length === 0 ? (
                <p className="text-sm text-muted-foreground">No memories found.</p>
              ) : (
                <div className="space-y-3">
                  {displayedMemories.map((memory) => {
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
                            <p className="mt-2 text-sm text-muted-foreground">{memory.content || 'No content.'}</p>
                            <p className="mt-2 text-xs text-muted-foreground">
                              Created: {memory.created_at ? new Date(memory.created_at).toLocaleString() : 'Unknown'}
                            </p>
                          </div>
                          <div className="flex flex-col gap-2 min-w-44">
                            <div className="rounded-lg border border-border/60 p-3">
                              <p className="mb-2 flex items-center text-xs text-muted-foreground">
                                <Gauge className="mr-1.5 h-3.5 w-3.5" />
                                Importance
                              </p>
                              <div className="h-2 w-full rounded-full bg-secondary">
                                <div className="h-2 rounded-full bg-primary" style={{ width: `${score * 100}%` }} />
                              </div>
                              <p className="mt-1 text-xs text-muted-foreground">{(score * 100).toFixed(1)}%</p>
                            </div>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => deleteMemory(memory.id)}
                              className="w-full"
                            >
                              <Trash2 className="mr-1 h-3.5 w-3.5" />
                              Delete
                            </Button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="session">
          <Card>
            <CardHeader>
              <CardTitle>Session Context Management</CardTitle>
              <CardDescription>Clear all memories for a specific session.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter session ID (e.g., sdk_abcd1234)"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                />
                <Button
                  onClick={clearSessionContext}
                  disabled={clearingSession || !sessionId.trim()}
                  variant="destructive"
                >
                  {clearingSession ? 'Clearing...' : 'Clear Session'}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                This will soft-delete all memory entries associated with the session ID from both Redis and the database.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="policies">
          <Card>
            <CardHeader>
              <CardTitle>Memory Retention Policies</CardTitle>
              <CardDescription>Active policies enforcing memory lifecycle and limits.</CardDescription>
            </CardHeader>
            <CardContent>
              {loadingPolicies ? (
                <p className="text-sm text-muted-foreground">Loading policies...</p>
              ) : policies.length === 0 ? (
                <p className="text-sm text-muted-foreground">No retention policies configured.</p>
              ) : (
                <div className="space-y-3">
                  {policies.map((policy) => (
                    <div key={policy.id} className="rounded-xl border border-border/70 p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium">{policy.name}</p>
                          <p className="text-sm text-muted-foreground">{policy.type}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm">
                            <Badge variant="outline">Max: {policy.max_count}</Badge>
                          </p>
                          <p className="text-xs text-muted-foreground mt-2">
                            TTL: {policy.ttl_days} days | Min importance: {(policy.min_importance * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            Memory Notes
          </CardTitle>
          <CardDescription>
            Memories are scoped to the logged-in user. Semantic search uses vector embeddings from Qdrant.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
