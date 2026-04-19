'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { Upload, FileText, Settings2, Trash2, CheckCircle2, MessageSquarePlus } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

interface KnowledgeSource {
  id: string
  name: string
  description: string
  type: string
  category: string
  status: string
  file_size: number
  chunk_count: number
  tags: string[]
  can_use_in_knowledge: boolean
  can_use_in_chat: boolean
  can_use_in_search: boolean
  is_active: boolean
  created_at: string
  client_id?: string
  source_name?: string
}

interface Conversation {
  id: string
  session_id: string
  title: string | null
  message_count: number
  created_at: string
}

export default function KnowledgePage() {
  const { token, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState(() => typeof window !== 'undefined' ? localStorage.getItem('knowledgeTab') || 'document' : 'document')
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showArticleModal, setShowArticleModal] = useState(false)
  const [showConversionModal, setShowConversionModal] = useState(false)
  const [selectedConvId, setSelectedConvId] = useState<string>('')
  const [converting, setConverting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [articleForm, setArticleForm] = useState({
    name: '',
    description: '',
    content: '',
    tags: '',
    client_id: '',
  })

  const categories = ['document', 'article', 'chat_session', 'client_document', 'training_material', 'reference']
  const categoryLabel: Record<string, string> = {
    document: 'Documents',
    article: 'Article',
    chat_session: 'Chat Session',
    client_document: 'Client Document',
    training_material: 'Training Material',
    reference: 'Reference',
  }

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchSources()
      if (activeTab === 'chat_session') {
        fetchConversations()
      }
    }
  }, [activeTab, isAuthenticated, token])

  useEffect(() => {
    localStorage.setItem('knowledgeTab', activeTab)
  }, [activeTab])

  const fetchSources = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/knowledge/sources?category=${activeTab}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        setSources(Array.isArray(data) ? data : data.items || [])
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch {
      setError('Failed to load knowledge sources')
    } finally {
      setLoading(false)
    }
  }

  const fetchConversations = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return
    try {
      const res = await fetch('/api/v1/chat/conversations?page=1&page_size=100', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        setConversations(data.items || [])
      }
    } catch {
      // no-op
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    const authToken = token || localStorage.getItem('access_token')
    if (!file || !authToken) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', file.name)
    formData.append('category', activeTab)

    try {
      const res = await fetch('/api/v1/knowledge/sources', {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body: formData,
      })
      if (res.ok) {
        setShowUploadModal(false)
        toast.success('Source uploaded successfully')
        fetchSources()
      } else {
        setError('Upload failed')
        toast.error('Upload failed')
      }
    } catch (e) {
      setError('Upload failed: ' + String(e))
      toast.error('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleArticleCreate = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return
    try {
      const res = await fetch('/api/v1/knowledge/articles', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: articleForm.name,
          description: articleForm.description,
          content: articleForm.content,
          tags: articleForm.tags.split(',').map((t) => t.trim()),
          category: 'article',
          client_id: articleForm.client_id || null,
        }),
      })
      if (res.ok) {
        setShowArticleModal(false)
        setArticleForm({ name: '', description: '', content: '', tags: '', client_id: '' })
        toast.success('Article created successfully')
        fetchSources()
      } else {
        setError('Failed to create article')
        toast.error('Failed to create article')
      }
    } catch (e) {
      setError('Failed to create article: ' + String(e))
      toast.error('Failed to create article')
    }
  }

  const handleConvertConversation = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken || !selectedConvId) return

    setConverting(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/knowledge/sources/from-conversation/${selectedConvId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        setShowConversionModal(false)
        setSelectedConvId('')
        toast.success('Conversation added to knowledge')
        fetchSources()
      } else if (res.status === 409) {
        setError('This conversation is already in the knowledge base')
        toast.warning('This conversation is already in the knowledge base')
      } else {
        setError('Failed to convert conversation')
        toast.error('Failed to convert conversation')
      }
    } catch (e) {
      setError('Failed to convert conversation: ' + String(e))
      toast.error('Failed to convert conversation')
    } finally {
      setConverting(false)
    }
  }

  const handleToggleUsage = async (
    sourceId: string,
    field: 'can_use_in_knowledge' | 'can_use_in_chat' | 'can_use_in_search'
  ) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return
    try {
      const source = sources.find((s) => s.id === sourceId)
      if (!source) return

      const newValue = !source[field]
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ [field]: newValue }),
      })
      if (res.ok) {
        fetchSources()
      }
    } catch (e) {
      setError('Failed to update source: ' + String(e))
      toast.error('Failed to update source')
    }
  }

  const handleDelete = async (sourceId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    try {
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        toast.success('Knowledge source deleted')
        fetchSources()
      }
    } catch (e) {
      setError('Failed to delete source: ' + String(e))
      toast.error('Failed to delete source')
    }
  }

  const handleApprove = async (sourceId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return
    try {
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}/approve`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        toast.success('Source approved')
        fetchSources()
      }
    } catch (e) {
      setError('Failed to approve: ' + String(e))
      toast.error('Failed to approve source')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Knowledge</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Knowledge Operations Hub</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Manage ingestion pipelines, article authoring, and conversion from conversation memory.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/knowledge/settings">
              <Button variant="outline">
                <Settings2 className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </Link>
            {activeTab === 'article' ? (
              <Button onClick={() => setShowArticleModal(true)}>
                <FileText className="mr-2 h-4 w-4" />
                New Article
              </Button>
            ) : activeTab === 'chat_session' ? (
              <Button onClick={() => setShowConversionModal(true)}>
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                Add from Conversation
              </Button>
            ) : (
              <Button onClick={() => setShowUploadModal(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Upload
              </Button>
            )}
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0">
          {categories.map((tab) => {
            return <TabsTrigger key={tab} value={tab}>{categoryLabel[tab] || tab}</TabsTrigger>
          })}
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Knowledge Sources</CardTitle>
          <CardDescription>
            Category: <span className="capitalize">{(categoryLabel[activeTab] || activeTab).toLowerCase()}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading sources...</p>
          ) : sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sources in this category yet.</p>
          ) : (
            <div className="space-y-4">
              {sources.map((source) => (
                <div key={source.id} className="rounded-xl border border-border/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{source.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{source.description || 'No description provided.'}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge variant={source.status === 'approved' ? 'success' : 'warning'}>{source.status}</Badge>
                        <Badge variant="outline">{source.type}</Badge>
                        {source.client_id && <Badge variant="secondary">Client: {source.client_id}</Badge>}
                      </div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      {source.file_size ? <p>{(source.file_size / 1024).toFixed(1)} KB</p> : null}
                      <p>{source.chunk_count} chunks</p>
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 rounded-lg border border-border/60 bg-secondary/30 p-3 sm:grid-cols-3">
                    <label className="flex items-center justify-between text-sm">
                      <span>Use in Knowledge</span>
                      <Switch
                        checked={source.can_use_in_knowledge}
                        onCheckedChange={() => handleToggleUsage(source.id, 'can_use_in_knowledge')}
                      />
                    </label>
                    <label className="flex items-center justify-between text-sm">
                      <span>Use in Chat</span>
                      <Switch
                        checked={source.can_use_in_chat}
                        onCheckedChange={() => handleToggleUsage(source.id, 'can_use_in_chat')}
                      />
                    </label>
                    <label className="flex items-center justify-between text-sm">
                      <span>Use in Search</span>
                      <Switch
                        checked={source.can_use_in_search}
                        onCheckedChange={() => handleToggleUsage(source.id, 'can_use_in_search')}
                      />
                    </label>
                  </div>

                  <div className="mt-3 flex gap-2">
                    {source.status === 'pending' && (
                      <Button size="sm" variant="secondary" onClick={() => handleApprove(source.id)}>
                        <CheckCircle2 className="mr-1.5 h-4 w-4" />
                        Approve
                      </Button>
                    )}
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button size="sm" variant="destructive">
                          <Trash2 className="mr-1.5 h-4 w-4" />
                          Delete
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete this knowledge source?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This action cannot be undone and will remove indexed chunks permanently.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDelete(source.id)}>Delete Source</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Upload {activeTab.replace(/_/g, ' ')}</DialogTitle>
            <DialogDescription>Select a file to ingest into knowledge.</DialogDescription>
          </DialogHeader>
          <Input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            accept=".pdf,.docx,.txt,.csv,.json,.xlsx,.xls,.html"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadModal(false)}>Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showArticleModal} onOpenChange={setShowArticleModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Article</DialogTitle>
            <DialogDescription>Author structured content for retrieval.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              placeholder="Article title"
              value={articleForm.name}
              onChange={(e) => setArticleForm({ ...articleForm, name: e.target.value })}
            />
            <Textarea
              placeholder="Description"
              rows={3}
              value={articleForm.description}
              onChange={(e) => setArticleForm({ ...articleForm, description: e.target.value })}
            />
            <Textarea
              placeholder="Article content"
              rows={8}
              value={articleForm.content}
              onChange={(e) => setArticleForm({ ...articleForm, content: e.target.value })}
            />
            <Input
              placeholder="Tags (comma separated)"
              value={articleForm.tags}
              onChange={(e) => setArticleForm({ ...articleForm, tags: e.target.value })}
            />
            <Input
              placeholder="Client ID (optional)"
              value={articleForm.client_id}
              onChange={(e) => setArticleForm({ ...articleForm, client_id: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowArticleModal(false)}>Cancel</Button>
            <Button onClick={handleArticleCreate}>Create Article</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showConversionModal} onOpenChange={setShowConversionModal}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Add Conversation to Knowledge</DialogTitle>
            <DialogDescription>Promote a chat session into a reusable source.</DialogDescription>
          </DialogHeader>
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {conversations.length === 0 ? (
              <p className="text-sm text-muted-foreground">No conversations available.</p>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConvId(conv.id)}
                  className={`w-full rounded-xl border p-3 text-left ${
                    selectedConvId === conv.id ? 'border-primary bg-primary/5' : 'border-border/70 hover:bg-secondary/30'
                  }`}
                >
                  <p className="text-sm font-medium">{conv.title || 'Untitled'}</p>
                  <p className="text-xs text-muted-foreground">
                    {conv.message_count} messages • {new Date(conv.created_at).toLocaleDateString()}
                  </p>
                </button>
              ))
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowConversionModal(false)
                setSelectedConvId('')
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleConvertConversation} disabled={!selectedConvId || converting}>
              {converting ? 'Converting...' : 'Add to Knowledge'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
