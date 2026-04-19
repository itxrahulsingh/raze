'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, Loader2, Plus, RefreshCcw, Search, ShieldCheck, Trash2, Wrench, Edit, Play, ChevronDown } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

interface ToolItem {
  id: string
  name: string
  display_name?: string | null
  description?: string
  type?: string
  schema?: Record<string, any>
  endpoint_url?: string
  method?: string
  auth_type?: string
  timeout_seconds?: number
  max_retries?: number
  usage_count?: number
  success_rate?: number
  avg_latency_ms?: number
  last_used?: string | null
  is_active?: boolean
  tags?: string[]
}

interface ToolExecution {
  id: string
  status: string
  latency_ms?: number
  executed_at?: string
  error_message?: string
  output_data?: any
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editingTool, setEditingTool] = useState<ToolItem | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [testingTool, setTestingTool] = useState<ToolItem | null>(null)
  const [testOpen, setTestOpen] = useState(false)
  const [executions, setExecutions] = useState<ToolExecution[]>([])
  const [loadingExecutions, setLoadingExecutions] = useState(false)
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null)

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

  const fetchTools = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
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
  }, [token])

  const fetchExecutions = useCallback(async (toolId: string) => {
    setLoadingExecutions(true)
    try {
      const res = await fetch(`/api/v1/tools/${toolId}/executions?limit=10`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setExecutions(Array.isArray(data) ? data : data.items || [])
      }
    } catch (err) {
      console.error('Failed to fetch executions:', err)
    } finally {
      setLoadingExecutions(false)
    }
  }, [token])

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
    const total = tools.length
    const active = tools.filter(t => t.is_active).length
    const totalUsage = tools.reduce((acc, tool) => acc + (tool.usage_count || 0), 0)
    const avgSuccess = total === 0 ? 0 : tools.reduce((acc, tool) => acc + ((tool.success_rate || 0) * 100), 0) / total
    return { total, active, totalUsage, avgSuccess }
  }, [tools])

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData)

    try {
      const res = await fetch('/api/v1/tools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: data.name,
          display_name: data.display_name || null,
          description: data.description,
          type: data.type || 'http_api',
          schema: data.schema ? JSON.parse(data.schema as string) : {},
          endpoint_url: data.endpoint_url,
          method: data.method || 'POST',
          auth_type: data.auth_type || 'none',
          timeout_seconds: parseInt(data.timeout_seconds as string) || 30,
          tags: (data.tags as string)?.split(',').map(t => t.trim()).filter(Boolean) || [],
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Tool created successfully')
      setCreateOpen(false)
      fetchTools()
    } catch (err) {
      toast.error(`Failed to create tool: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleUpdate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editingTool) return

    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData)

    try {
      const res = await fetch(`/api/v1/tools/${editingTool.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          display_name: data.display_name || null,
          description: data.description,
          schema: data.schema ? JSON.parse(data.schema as string) : editingTool.schema,
          endpoint_url: data.endpoint_url,
          method: data.method,
          auth_type: data.auth_type,
          timeout_seconds: parseInt(data.timeout_seconds as string) || 30,
          tags: (data.tags as string)?.split(',').map(t => t.trim()).filter(Boolean) || [],
          is_active: data.is_active === 'on',
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Tool updated successfully')
      setEditOpen(false)
      fetchTools()
    } catch (err) {
      toast.error(`Failed to update tool: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (toolId: string, toolName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${toolName}"?`)) return

    try {
      const res = await fetch(`/api/v1/tools/${toolId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to delete')
      toast.success('Tool deleted successfully')
      fetchTools()
    } catch (err) {
      toast.error(`Failed to delete tool: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleTest = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!testingTool) return

    const formData = new FormData(e.currentTarget)
    const inputData = JSON.parse((formData.get('input_data') as string) || '{}')

    try {
      const res = await fetch(`/api/v1/tools/${testingTool.id}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(inputData),
      })
      if (!res.ok) throw new Error(await res.text())
      const result = await res.json()
      toast.success('Tool test completed')
      console.log('Test result:', result)
    } catch (err) {
      toast.error(`Test failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Tooling</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Tool Management</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Create, manage, test, and monitor operational tools.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchTools} disabled={loading}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Tool
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create New Tool</DialogTitle>
                  <DialogDescription>Register a new tool for AI execution</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreate} className="space-y-4">
                  <input type="text" name="name" placeholder="Tool name (snake_case)" required className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <input type="text" name="display_name" placeholder="Display name (optional)" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <textarea name="description" placeholder="Description" required className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <select name="type" className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                    <option value="http_api">HTTP API</option>
                    <option value="database">Database</option>
                    <option value="function">Function</option>
                  </select>
                  <input type="text" name="endpoint_url" placeholder="Endpoint URL" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <select name="method" className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                    <option value="POST">POST</option>
                    <option value="GET">GET</option>
                    <option value="PUT">PUT</option>
                  </select>
                  <select name="auth_type" className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                    <option value="none">None</option>
                    <option value="api_key">API Key</option>
                    <option value="bearer">Bearer</option>
                    <option value="basic">Basic</option>
                  </select>
                  <input type="number" name="timeout_seconds" placeholder="Timeout (seconds)" defaultValue="30" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <textarea name="schema" placeholder='OpenAI function schema (JSON)' className="w-full rounded border border-input bg-background px-3 py-2 text-sm font-mono text-xs" />
                  <input type="text" name="tags" placeholder="Tags (comma-separated)" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <Button type="submit" className="w-full">Create Tool</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Tools</CardDescription>
            <CardTitle className="text-3xl">{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl">{summary.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Executions</CardDescription>
            <CardTitle className="text-3xl">{summary.totalUsage.toLocaleString()}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Success Rate</CardDescription>
            <CardTitle className="text-3xl">{summary.avgSuccess.toFixed(1)}%</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registered Tools</CardTitle>
          <CardDescription>Create, test, and manage tools.</CardDescription>
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
            <p className="text-sm text-muted-foreground">No tools found. Create your first tool to get started.</p>
          ) : (
            <div className="space-y-3">
              {filteredTools.map((tool) => (
                <div key={tool.id} className="rounded-xl border border-border/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="font-semibold">{tool.display_name || tool.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {tool.description || 'No description'}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Dialog open={testOpen && testingTool?.id === tool.id} onOpenChange={(open) => { if (open) { setTestingTool(tool); fetchExecutions(tool.id); } setTestOpen(open) }}>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="outline" onClick={() => setTestingTool(tool)}>
                            <Play className="mr-1 h-3.5 w-3.5" />
                            Test
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl">
                          <DialogHeader>
                            <DialogTitle>Test Tool: {tool.name}</DialogTitle>
                          </DialogHeader>
                          <form onSubmit={handleTest} className="space-y-4">
                            <textarea name="input_data" placeholder='Input JSON (e.g., {"param": "value"})' defaultValue="{}" className="w-full rounded border border-input bg-background px-3 py-2 text-sm font-mono" rows={6} />
                            <Button type="submit" className="w-full">Execute Test</Button>
                          </form>
                        </DialogContent>
                      </Dialog>
                      <Dialog open={editOpen && editingTool?.id === tool.id} onOpenChange={(open) => { if (open) setEditingTool(tool); setEditOpen(open) }}>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="outline">
                            <Edit className="mr-1 h-3.5 w-3.5" />
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl">
                          <DialogHeader>
                            <DialogTitle>Edit Tool</DialogTitle>
                          </DialogHeader>
                          {editingTool && (
                            <form onSubmit={handleUpdate} className="space-y-4">
                              <input type="text" name="display_name" placeholder="Display name" defaultValue={editingTool.display_name || ''} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                              <textarea name="description" placeholder="Description" defaultValue={editingTool.description || ''} required className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                              <input type="text" name="endpoint_url" placeholder="Endpoint URL" defaultValue={editingTool.endpoint_url || ''} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                              <select name="method" defaultValue={editingTool.method || 'POST'} className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                                <option value="POST">POST</option>
                                <option value="GET">GET</option>
                                <option value="PUT">PUT</option>
                              </select>
                              <select name="auth_type" defaultValue={editingTool.auth_type || 'none'} className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                                <option value="none">None</option>
                                <option value="api_key">API Key</option>
                                <option value="bearer">Bearer</option>
                              </select>
                              <input type="number" name="timeout_seconds" defaultValue={editingTool.timeout_seconds || 30} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                              <textarea name="schema" placeholder='Schema (JSON)' defaultValue={JSON.stringify(editingTool.schema || {}, null, 2)} className="w-full rounded border border-input bg-background px-3 py-2 text-sm font-mono text-xs" rows={5} />
                              <div className="flex items-center gap-2">
                                <input type="checkbox" name="is_active" id="is_active" defaultChecked={editingTool.is_active} className="h-4 w-4 rounded border-input" />
                                <label htmlFor="is_active" className="text-sm">Active</label>
                              </div>
                              <input type="text" name="tags" placeholder="Tags (comma-separated)" defaultValue={editingTool.tags?.join(', ') || ''} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                              <Button type="submit" className="w-full">Update Tool</Button>
                            </form>
                          )}
                        </DialogContent>
                      </Dialog>
                      <Button size="sm" variant="destructive" onClick={() => handleDelete(tool.id, tool.name)}>
                        <Trash2 className="mr-1 h-3.5 w-3.5" />
                        Delete
                      </Button>
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
                    <p>Latency: {Math.round(tool.avg_latency_ms || 0)}ms | Last used: {tool.last_used ? new Date(tool.last_used).toLocaleString() : 'Never'}</p>
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
