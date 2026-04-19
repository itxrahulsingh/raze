'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { BookPlus, ChevronLeft, ChevronRight, Cpu, MessageSquare, Search, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { useAuth } from '@/lib/auth-context'
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
}

interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  model_used?: string
  tokens_used?: number
  latency_ms?: number
  created_at: string
}

const ITEMS_PER_PAGE = 12

export default function ConversationsPage() {
  const { token, isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState<ConversationDetail[]>([])
  const [selectedConvId, setSelectedConvId] = useState<string>('')
  const [selectedMessages, setSelectedMessages] = useState<ConversationMessage[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [totalConversations, setTotalConversations] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [convertingToKnowledge, setConvertingToKnowledge] = useState<string | null>(null)

  const initialHydratedRef = useRef(false)

  const totalPages = Math.max(1, Math.ceil(totalConversations / ITEMS_PER_PAGE))
  const selectedConversation = useMemo(
    () => conversations.find((item) => item.id === selectedConvId),
    [conversations, selectedConvId]
  )

  const getToken = useCallback(() => token || localStorage.getItem('access_token'), [token])

  const readConversationFromUrl = () => {
    if (typeof window === 'undefined') return ''
    const params = new URLSearchParams(window.location.search)
    return params.get('conversation') || ''
  }

  const syncConversationInUrl = (conversationId: string) => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (conversationId) params.set('conversation', conversationId)
    else params.delete('conversation')
    const query = params.toString()
    window.history.replaceState({}, '', query ? `/conversations?${query}` : '/conversations')
  }

  const fetchConversations = useCallback(
    async (pageNum: number) => {
      const authToken = getToken()
      if (!authToken) return

      setLoadingList(true)
      setError(null)
      try {
        const res = await fetch(`/api/v1/chat/conversations?page=${pageNum}&page_size=${ITEMS_PER_PAGE}`, {
          headers: { Authorization: `Bearer ${authToken}` },
        })
        if (!res.ok) {
          throw new Error(`Failed to load conversations (${res.status})`)
        }

        const data = await res.json()
        setConversations(data.items || [])
        setTotalConversations(data.total || 0)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversations')
      } finally {
        setLoadingList(false)
      }
    },
    [getToken]
  )

  const fetchConversationById = useCallback(
    async (conversationId: string) => {
      const authToken = getToken()
      if (!authToken) return null
      try {
        const res = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
          headers: { Authorization: `Bearer ${authToken}` },
        })
        if (!res.ok) return null
        const conversation = (await res.json()) as ConversationDetail
        setConversations((prev) => {
          if (prev.some((item) => item.id === conversation.id)) return prev
          return [conversation, ...prev]
        })
        return conversation
      } catch {
        return null
      }
    },
    [getToken]
  )

  const loadConversationMessages = useCallback(
    async (convId: string) => {
      const authToken = getToken()
      if (!authToken) return

      setLoadingMessages(true)
      setError(null)
      setSelectedConvId(convId)
      syncConversationInUrl(convId)

      try {
        const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=200`, {
          headers: { Authorization: `Bearer ${authToken}` },
        })
        if (!res.ok) {
          throw new Error(`Failed to load messages (${res.status})`)
        }

        const data = await res.json()
        setSelectedMessages(data.items || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load messages')
      } finally {
        setLoadingMessages(false)
      }
    },
    [getToken]
  )

  const deleteConversation = useCallback(
    async (convId: string) => {
      const authToken = getToken()
      if (!authToken) return

      try {
        const res = await fetch(`/api/v1/chat/conversations/${convId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${authToken}` },
        })
        if (!res.ok) throw new Error(`Failed to delete conversation (${res.status})`)

        toast.success('Conversation deleted')
        if (selectedConvId === convId) {
          setSelectedConvId('')
          setSelectedMessages([])
          syncConversationInUrl('')
        }
        await fetchConversations(page)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete conversation')
      }
    },
    [fetchConversations, getToken, page, selectedConvId]
  )

  const handleAddToKnowledge = useCallback(
    async (convId: string) => {
      const authToken = getToken()
      if (!authToken) return

      setConvertingToKnowledge(convId)
      try {
        const res = await fetch(`/api/v1/knowledge/sources/from-conversation/${convId}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}` },
        })

        if (res.ok) {
          toast.success('Conversation added to knowledge base')
          return
        }
        if (res.status === 409) {
          toast.warning('This conversation is already in the knowledge base')
          return
        }
        throw new Error(`Failed to add to knowledge (${res.status})`)
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to add to knowledge base')
      } finally {
        setConvertingToKnowledge(null)
      }
    },
    [getToken]
  )

  useEffect(() => {
    if (!isAuthenticated) return
    fetchConversations(page)
  }, [fetchConversations, isAuthenticated, page])

  useEffect(() => {
    if (!isAuthenticated || loadingList || initialHydratedRef.current) return
      const convFromUrl = readConversationFromUrl()
      if (convFromUrl) {
        const found = conversations.find((item) => item.id === convFromUrl)
        if (found) {
          loadConversationMessages(found.id)
        } else {
          fetchConversationById(convFromUrl).then((fetched) => {
            if (fetched) {
              loadConversationMessages(fetched.id)
            } else {
              syncConversationInUrl('')
            }
          })
        }
        initialHydratedRef.current = true
        return
    }

    if (conversations.length > 0) {
      loadConversationMessages(conversations[0].id)
    }
    initialHydratedRef.current = true
  }, [conversations, fetchConversationById, isAuthenticated, loadingList, loadConversationMessages])

  useEffect(() => {
    const onPopState = () => {
      const convFromUrl = readConversationFromUrl()
      if (!convFromUrl || convFromUrl === selectedConvId) return
      const found = conversations.find((item) => item.id === convFromUrl)
      if (found) {
        loadConversationMessages(found.id)
        return
      }
      fetchConversationById(convFromUrl).then((fetched) => {
        if (fetched) loadConversationMessages(fetched.id)
      })
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [conversations, fetchConversationById, loadConversationMessages, selectedConvId])

  const filteredConversations = useMemo(
    () =>
      conversations.filter((item) => (item.title || 'Untitled').toLowerCase().includes(searchTerm.toLowerCase())),
    [conversations, searchTerm]
  )

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Conversations</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Session Intelligence Console</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Review live and historical sessions, inspect model behavior, and promote valuable chats to knowledge.
            </p>
          </div>
          <Badge variant="secondary">{totalConversations} total sessions</Badge>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="min-h-[650px]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Conversation List</CardTitle>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search conversation title..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </div>
          </CardHeader>

          <CardContent className="space-y-2">
            {loadingList ? (
              <p className="text-sm text-muted-foreground">Loading conversations...</p>
            ) : filteredConversations.length === 0 ? (
              <p className="text-sm text-muted-foreground">No conversations found on this page.</p>
            ) : (
              filteredConversations.map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => loadConversationMessages(conversation.id)}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    selectedConvId === conversation.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border/70 hover:bg-secondary/40'
                  }`}
                >
                  <p className="truncate text-sm font-medium">{conversation.title || 'Untitled'}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {conversation.message_count} msgs • {new Date(conversation.created_at).toLocaleDateString()}
                  </p>
                </button>
              ))
            )}

            <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-3">
              <Button variant="outline" size="sm" onClick={() => setPage((prev) => Math.max(1, prev - 1))} disabled={page === 1}>
                <ChevronLeft className="mr-1 h-4 w-4" />
                Prev
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={page >= totalPages}
              >
                Next
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="min-h-[650px]">
          {selectedConvId && selectedConversation ? (
            <>
              <CardHeader className="border-b border-border/70 pb-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>{selectedConversation.title || 'Untitled Conversation'}</CardTitle>
                    <CardDescription>{new Date(selectedConversation.created_at).toLocaleString()}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/admin-chat?conversation=${selectedConvId}`}>
                      <Button size="sm" variant="outline">Open in Admin Chat</Button>
                    </Link>
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
                            This permanently removes the conversation and all message history.
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
                    <p className="mt-1 text-base font-semibold">{selectedConversation.message_count}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Tokens</p>
                    <p className="mt-1 text-base font-semibold">{selectedConversation.total_tokens}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Cost</p>
                    <p className="mt-1 text-base font-semibold">${selectedConversation.total_cost_usd.toFixed(4)}</p>
                  </div>
                  <div className="rounded-lg border border-border/70 p-2.5 text-xs">
                    <p className="text-muted-foreground">Status</p>
                    <p className="mt-1 text-base font-semibold capitalize">{selectedConversation.status}</p>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="h-[490px] space-y-3 overflow-y-auto py-4">
                {loadingMessages ? (
                  <p className="text-sm text-muted-foreground">Loading messages...</p>
                ) : selectedMessages.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No messages in this conversation.</p>
                ) : (
                  selectedMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`rounded-xl border p-3 ${
                        message.role === 'user'
                          ? 'ml-8 border-primary/30 bg-primary/5'
                          : 'mr-8 border-border/70 bg-secondary/30'
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                        <span className="font-medium">{message.role === 'user' ? 'User' : 'Assistant'}</span>
                        <span>{new Date(message.created_at).toLocaleTimeString()}</span>
                      </div>
                      <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                      {message.model_used ? (
                        <p className="mt-2 inline-flex items-center text-xs text-muted-foreground">
                          <Cpu className="mr-1.5 h-3.5 w-3.5" />
                          {message.model_used}
                          {message.tokens_used ? ` • ${message.tokens_used} tokens` : ''}
                          {message.latency_ms ? ` • ${message.latency_ms}ms` : ''}
                        </p>
                      ) : null}
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
