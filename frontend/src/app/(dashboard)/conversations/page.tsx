'use client'

import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/lib/auth-context'
import { MessageSquare, Search, Trash2, BookPlus, ChevronLeft, ChevronRight, Cpu } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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

interface ConversationDetail {
  id: string
  session_id: string
  title: string | null
  message_count: number
  total_tokens: number
  total_cost_usd: number
  status: string
  created_at: string
  updated_at: string
  conv_metadata?: {
    ip_address?: string
    country?: string
    city?: string
    user_agent?: string
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  model_used?: string
  tokens_used?: number
  latency_ms?: number
  created_at: string
}

export default function ConversationsPage() {
  const { token, isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState<ConversationDetail[]>([])
  const [selectedConvId, setSelectedConvId] = useState<string>('')
  const [selectedMessages, setSelectedMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [totalConversations, setTotalConversations] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [convertingToKnowledge, setConvertingToKnowledge] = useState<string | null>(null)

  const itemsPerPage = 10

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchConversations(page)
    }
  }, [page, isAuthenticated, token])

  const fetchConversations = async (pageNum: number) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    setLoading(true)
    try {
      const res = await fetch(`/api/v1/chat/conversations?page=${pageNum}&page_size=${itemsPerPage}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })

      if (res.ok) {
        const data = await res.json()
        setConversations(data.items || [])
        setTotalConversations(data.total || 0)
        setError(null)
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch {
      setError('Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }

  const loadConversationMessages = async (convId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    setLoadingMessages(true)
    setSelectedConvId(convId)
    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=100`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })

      if (res.ok) {
        const data = await res.json()
        setSelectedMessages(data.items || [])
        setError(null)
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch {
      setError('Failed to load messages')
    } finally {
      setLoadingMessages(false)
    }
  }

  const deleteConversation = async (convId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      })

      if (res.ok) {
        fetchConversations(page)
        if (selectedConvId === convId) {
          setSelectedConvId('')
          setSelectedMessages([])
        }
        setError(null)
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch {
      setError('Failed to delete conversation')
    }
  }

  const handleAddToKnowledge = async (convId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    setConvertingToKnowledge(convId)
    try {
      const res = await fetch(`/api/v1/knowledge/sources/from-conversation/${convId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
      })

      if (res.ok) {
        setError(null)
        toast.success('Conversation added to knowledge base')
      } else if (res.status === 409) {
        setError('This conversation is already in the knowledge base')
        toast.warning('This conversation is already in the knowledge base')
      } else {
        setError('Failed to add conversation to knowledge base')
        toast.error('Failed to add conversation to knowledge base')
      }
    } catch (e) {
      setError('Failed to add conversation to knowledge base: ' + String(e))
      toast.error('Failed to add conversation to knowledge base')
    } finally {
      setConvertingToKnowledge(null)
    }
  }

  const filteredConversations = useMemo(
    () =>
      conversations.filter((c) =>
        (c.title || 'Untitled').toLowerCase().includes(searchTerm.toLowerCase())
      ),
    [conversations, searchTerm]
  )

  const totalPages = Math.ceil(totalConversations / itemsPerPage)
  const currentConv = conversations.find((c) => c.id === selectedConvId)

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Conversations</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Session Intelligence Console</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Review live and historical conversations, inspect model behavior, and promote valuable sessions to knowledge.
            </p>
          </div>
          <Badge variant="secondary">{totalConversations} total sessions</Badge>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <Card className="min-h-[620px]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Conversation List</CardTitle>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search conversations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading conversations...</p>
            ) : filteredConversations.length === 0 ? (
              <p className="text-sm text-muted-foreground">No conversations found.</p>
            ) : (
              <div className="space-y-2">
                {filteredConversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversationMessages(conv.id)}
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      selectedConvId === conv.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border/70 hover:bg-secondary/40'
                    }`}
                  >
                    <p className="truncate text-sm font-medium">{conv.title || 'Untitled'}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {conv.message_count} messages • {new Date(conv.created_at).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-border/60 pt-3">
                <Button size="sm" variant="outline" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Prev
                </Button>
                <span className="text-xs text-muted-foreground">
                  Page {page} / {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-h-[620px]">
          {selectedConvId && currentConv ? (
            <>
              <CardHeader className="border-b border-border/70 pb-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>{currentConv.title || 'Untitled Conversation'}</CardTitle>
                    <CardDescription>{new Date(currentConv.created_at).toLocaleString()}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleAddToKnowledge(selectedConvId)}
                      disabled={convertingToKnowledge === selectedConvId}
                    >
                      <BookPlus className="mr-1.5 h-4 w-4" />
                      {convertingToKnowledge === selectedConvId ? 'Adding...' : 'Add to Knowledge'}
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button size="sm" variant="destructive">
                          <Trash2 className="mr-1.5 h-4 w-4" />
                          Delete
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This permanently removes the conversation and message history.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => deleteConversation(selectedConvId)}>
                            Delete Conversation
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>

                <div className="grid gap-2 sm:grid-cols-4">
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Messages</p>
                    <p className="mt-1 text-base font-semibold">{currentConv.message_count}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Tokens</p>
                    <p className="mt-1 text-base font-semibold">{currentConv.total_tokens}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Cost</p>
                    <p className="mt-1 text-base font-semibold">${currentConv.total_cost_usd.toFixed(4)}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Status</p>
                    <p className="mt-1 text-base font-semibold capitalize">{currentConv.status}</p>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="h-[460px] space-y-3 overflow-y-auto py-4">
                {loadingMessages ? (
                  <p className="text-sm text-muted-foreground">Loading messages...</p>
                ) : selectedMessages.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No messages.</p>
                ) : (
                  selectedMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`rounded-xl border p-3 ${
                        msg.role === 'user'
                          ? 'ml-8 border-primary/30 bg-primary/5'
                          : 'mr-8 border-border/70 bg-secondary/30'
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                        <span className="font-medium">{msg.role === 'user' ? 'User' : 'Assistant'}</span>
                        <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                      </div>
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                      {msg.model_used && (
                        <p className="mt-2 inline-flex items-center text-xs text-muted-foreground">
                          <Cpu className="mr-1.5 h-3.5 w-3.5" />
                          {msg.model_used}
                          {msg.tokens_used ? ` • ${msg.tokens_used} tokens` : ''}
                          {msg.latency_ms ? ` • ${msg.latency_ms}ms` : ''}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </CardContent>
            </>
          ) : (
            <CardContent className="grid h-full place-items-center text-center">
              <div>
                <MessageSquare className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">Select a conversation to view details.</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}
