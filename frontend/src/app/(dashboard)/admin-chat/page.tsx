'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Link as LinkIcon,
  Loader2,
  MessageSquarePlus,
  SendHorizontal,
  Sparkles,
  Trash2,
  UserRound,
} from 'lucide-react'
import { toast } from 'sonner'

import { useAuth } from '@/lib/auth-context'
import { useSettings } from '@/lib/settings-context'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

type Role = 'user' | 'assistant' | 'system' | 'tool'

type ChatMessage = {
  id: string
  conversation_id?: string
  role: Role
  content: string
  created_at: string
  model_used?: string | null
  tokens_used?: number | null
  latency_ms?: number | null
  tool_results?: unknown[] | null
  msg_metadata?: Record<string, unknown> | null
  isStreaming?: boolean
}

type Conversation = {
  id: string
  session_id: string
  title: string | null
  message_count: number
  created_at: string
}

type SseChunk = {
  event?: string
  text?: string
  message_id?: string
  conversation_id?: string
  tokens_used?: number
  latency_ms?: number
}

type SourceLink = {
  url: string
  label: string
}

const CONVERSATIONS_PAGE_SIZE = 20
const MESSAGES_PAGE_SIZE = 30
const URL_RE = /(https?:\/\/[^\s<>"'`)\]}]+)/gi

function makeSessionId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function toMessage(input: ChatMessage): ChatMessage {
  return {
    ...input,
    role: input.role ?? 'assistant',
    content: input.content ?? '',
  }
}

function hostnameFromUrl(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return 'Source'
  }
}

function addHttpLinks(value: unknown, sink: Set<string>) {
  if (typeof value === 'string') {
    const matches = value.match(URL_RE)
    if (matches) {
      for (const candidate of matches) sink.add(candidate)
    }
    return
  }

  if (Array.isArray(value)) {
    for (const item of value) addHttpLinks(item, sink)
    return
  }

  if (!value || typeof value !== 'object') return

  const obj = value as Record<string, unknown>
  const directUrlKeys = ['url', 'link', 'href', 'source_url', 'reference_url']
  for (const key of Object.keys(obj)) {
    if (directUrlKeys.includes(key) && typeof obj[key] === 'string') {
      sink.add(obj[key] as string)
    } else {
      addHttpLinks(obj[key], sink)
    }
  }
}

function extractSourceLinks(message: ChatMessage): SourceLink[] {
  const links = new Set<string>()
  addHttpLinks(message.content, links)
  addHttpLinks(message.tool_results, links)
  addHttpLinks(message.msg_metadata, links)

  return [...links]
    .filter((url) => /^https?:\/\//i.test(url))
    .slice(0, 8)
    .map((url) => ({
      url,
      label: hostnameFromUrl(url),
    }))
}

function LinkifiedText({ text }: { text: string }) {
  const parts = useMemo(() => text.split(URL_RE), [text])

  return (
    <span className="whitespace-pre-wrap break-words">
      {parts.map((part, idx) => {
        if (/^https?:\/\//i.test(part)) {
          return (
            <a
              key={`${part}-${idx}`}
              href={part}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline underline-offset-2 hover:opacity-80"
            >
              {part}
            </a>
          )
        }
        return <span key={`${part}-${idx}`}>{part}</span>
      })}
    </span>
  )
}

export default function AdminChatPage() {
  const settings = useSettings()
  const whiteLabelSettings =
    'whiteLabelSettings' in settings ? settings.whiteLabelSettings : settings
  const { token, isAuthenticated } = useAuth()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [convPage, setConvPage] = useState(1)
  const [hasMoreConversations, setHasMoreConversations] = useState(true)
  const [loadingConversations, setLoadingConversations] = useState(true)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [olderMessagesPage, setOlderMessagesPage] = useState<number | null>(null)

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [activeSessionId, setActiveSessionId] = useState<string>(makeSessionId())
  const [composer, setComposer] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [useKnowledge, setUseKnowledge] = useState(true)
  const [useMemory, setUseMemory] = useState(true)
  const [toolsEnabled, setToolsEnabled] = useState(true)

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [conversationFromUrl, setConversationFromUrl] = useState<string | null>(null)

  const activeConversationRef = useRef<string | null>(null)
  const initialConversationHydratedRef = useRef(false)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)

  const getToken = useCallback(() => token || localStorage.getItem('access_token'), [token])

  const scrollToBottom = useCallback((smooth = true) => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' })
  }, [])

  useEffect(() => {
    const readConversationFromUrl = () => {
      if (typeof window === 'undefined') return
      const params = new URLSearchParams(window.location.search)
      setConversationFromUrl(params.get('conversation'))
    }

    readConversationFromUrl()
    window.addEventListener('popstate', readConversationFromUrl)
    return () => window.removeEventListener('popstate', readConversationFromUrl)
  }, [])

  const syncConversationInUrl = useCallback(
    (conversationId: string | null) => {
      if (typeof window === 'undefined') return
      const params = new URLSearchParams(window.location.search)
      if (conversationId) {
        params.set('conversation', conversationId)
      } else {
        params.delete('conversation')
      }

      const query = params.toString()
      window.history.replaceState({}, '', query ? `/admin-chat?${query}` : '/admin-chat')
      setConversationFromUrl(conversationId)
    },
    []
  )

  const fetchConversations = useCallback(
    async (page = 1, append = false) => {
      const authToken = getToken()
      if (!authToken) return

      if (page === 1) setLoadingConversations(true)
      try {
        const res = await fetch(
          `/api/v1/chat/conversations?page=${page}&page_size=${CONVERSATIONS_PAGE_SIZE}`,
          { headers: { Authorization: `Bearer ${authToken}` } }
        )
        if (!res.ok) {
          throw new Error(`Failed to load conversations (${res.status})`)
        }

        const data = await res.json()
        const items = (data.items || []) as Conversation[]

        setConversations((prev) => (append ? [...prev, ...items] : items))
        setHasMoreConversations(items.length >= CONVERSATIONS_PAGE_SIZE)
        setConvPage(page)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load conversations'
        setError(msg)
      } finally {
        if (page === 1) setLoadingConversations(false)
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
        const conversation = (await res.json()) as Conversation
        setConversations((prev) => {
          const existingIndex = prev.findIndex((item) => item.id === conversation.id)
          if (existingIndex === 0) return prev
          if (existingIndex > 0) {
            const cloned = [...prev]
            cloned.splice(existingIndex, 1)
            return [conversation, ...cloned]
          }
          return [conversation, ...prev]
        })
        return conversation
      } catch {
        return null
      }
    },
    [getToken]
  )

  const loadLatestMessages = useCallback(
    async (conversationId: string) => {
      const authToken = getToken()
      if (!authToken) return

      setLoadingMessages(true)
      setError(null)

      try {
        const countRes = await fetch(
          `/api/v1/chat/conversations/${conversationId}/messages?page=1&page_size=1`,
          { headers: { Authorization: `Bearer ${authToken}` } }
        )
        if (!countRes.ok) {
          throw new Error(`Failed to load message count (${countRes.status})`)
        }
        const countData = await countRes.json()
        const total = Number(countData.total || 0)

        if (total === 0) {
          if (activeConversationRef.current === conversationId) {
            setMessages([])
            setOlderMessagesPage(null)
          }
          return
        }

        const lastPage = Math.max(1, Math.ceil(total / MESSAGES_PAGE_SIZE))
        const pageRes = await fetch(
          `/api/v1/chat/conversations/${conversationId}/messages?page=${lastPage}&page_size=${MESSAGES_PAGE_SIZE}`,
          { headers: { Authorization: `Bearer ${authToken}` } }
        )
        if (!pageRes.ok) {
          throw new Error(`Failed to load messages (${pageRes.status})`)
        }

        const pageData = await pageRes.json()
        const items = ((pageData.items || []) as ChatMessage[]).map(toMessage)

        if (activeConversationRef.current === conversationId) {
          setMessages(items)
          setOlderMessagesPage(lastPage > 1 ? lastPage - 1 : null)
          requestAnimationFrame(() => scrollToBottom(false))
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load messages'
        setError(msg)
      } finally {
        if (activeConversationRef.current === conversationId) {
          setLoadingMessages(false)
        }
      }
    },
    [getToken, scrollToBottom]
  )

  const loadOlderMessages = useCallback(async () => {
    if (!activeConversationId || !olderMessagesPage) return

    const authToken = getToken()
    if (!authToken) return

    const list = messagesContainerRef.current
    const previousHeight = list?.scrollHeight ?? 0

    try {
      const res = await fetch(
        `/api/v1/chat/conversations/${activeConversationId}/messages?page=${olderMessagesPage}&page_size=${MESSAGES_PAGE_SIZE}`,
        { headers: { Authorization: `Bearer ${authToken}` } }
      )
      if (!res.ok) throw new Error(`Failed to load older messages (${res.status})`)

      const data = await res.json()
      const older = ((data.items || []) as ChatMessage[]).map(toMessage)

      setMessages((prev) => [...older, ...prev])
      setOlderMessagesPage((prev) => (prev && prev > 1 ? prev - 1 : null))

      requestAnimationFrame(() => {
        const nextHeight = list?.scrollHeight ?? previousHeight
        if (list) list.scrollTop += nextHeight - previousHeight
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load older messages'
      setError(msg)
    }
  }, [activeConversationId, getToken, olderMessagesPage])

  const openConversation = useCallback(
    async (conversation: Conversation) => {
      setActiveConversationId(conversation.id)
      setActiveSessionId(conversation.session_id)
      activeConversationRef.current = conversation.id
      syncConversationInUrl(conversation.id)
      setMessages([])
      await loadLatestMessages(conversation.id)
    },
    [loadLatestMessages, syncConversationInUrl]
  )

  const startNewChat = useCallback(() => {
    setActiveConversationId(null)
    activeConversationRef.current = null
    syncConversationInUrl(null)
    setActiveSessionId(makeSessionId())
    setMessages([])
    setOlderMessagesPage(null)
    setComposer('')
    setError(null)
  }, [syncConversationInUrl])

  const sendMessage = useCallback(async () => {
    const messageText = composer.trim()
    const authToken = getToken()

    if (!messageText || !authToken || sending) return

    const sessionId = activeSessionId || makeSessionId()
    if (!activeSessionId) setActiveSessionId(sessionId)

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      created_at: new Date().toISOString(),
    }

    const assistantMessageId = `assistant-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        isStreaming: true,
      },
    ])
    setComposer('')
    setSending(true)
    setError(null)
    requestAnimationFrame(() => scrollToBottom())

    let buffer = ''
    let streamedText = ''
    let finalConversationId: string | undefined
    let finalMessageId: string | undefined
    let finalTokensUsed: number | undefined
    let finalLatency: number | undefined

    try {
      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          session_id: sessionId,
          use_knowledge: useKnowledge,
          use_memory: useMemory,
          tools_enabled: toolsEnabled,
        }),
      })

      if (!res.ok || !res.body) {
        throw new Error(`Chat request failed (${res.status})`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      const applyChunk = (chunk: SseChunk) => {
        if (chunk.event === 'start' && chunk.conversation_id) {
          finalConversationId = chunk.conversation_id
          return
        }

        if (chunk.event === 'delta' && chunk.text) {
          streamedText += chunk.text
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: streamedText } : msg
            )
          )
          return
        }

        if (chunk.event === 'done') {
          finalConversationId = chunk.conversation_id || finalConversationId
          finalMessageId = chunk.message_id
          finalTokensUsed = chunk.tokens_used
          finalLatency = chunk.latency_ms
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        let eventEnd = buffer.indexOf('\n\n')
        while (eventEnd !== -1) {
          const rawEvent = buffer.slice(0, eventEnd)
          buffer = buffer.slice(eventEnd + 2)

          const lines = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data: '))
            .map((line) => line.slice(6))
          const payload = lines.join('\n').trim()

          if (payload && payload !== '[DONE]') {
            try {
              applyChunk(JSON.parse(payload) as SseChunk)
            } catch {
              // Ignore malformed chunk and continue streaming.
            }
          }

          eventEnd = buffer.indexOf('\n\n')
        }
      }

      const now = new Date().toISOString()
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                id: finalMessageId || msg.id,
                content: streamedText || 'No response generated.',
                tokens_used: finalTokensUsed ?? msg.tokens_used,
                latency_ms: finalLatency ?? msg.latency_ms,
                created_at: now,
                isStreaming: false,
              }
            : msg
        )
      )

      if (finalConversationId && finalConversationId !== activeConversationId) {
        setActiveConversationId(finalConversationId)
        activeConversationRef.current = finalConversationId
        syncConversationInUrl(finalConversationId)
      }

      if (finalConversationId) {
        const resolved = await fetchConversationById(finalConversationId)
        if (resolved?.session_id) {
          setActiveSessionId(resolved.session_id)
        }
      }

      await fetchConversations(1, false)
      requestAnimationFrame(() => scrollToBottom())
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send message'
      setError(msg)
      setMessages((prev) =>
        prev.map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                content: `I hit an error while generating the reply.\n\n${msg}`,
                isStreaming: false,
              }
            : item
        )
      )
    } finally {
      setSending(false)
    }
  }, [
    activeConversationId,
    activeSessionId,
    composer,
    fetchConversations,
    fetchConversationById,
    getToken,
    scrollToBottom,
    sending,
    toolsEnabled,
    useKnowledge,
    useMemory,
    syncConversationInUrl,
  ])

  const confirmDeleteConversation = useCallback(async () => {
    if (!deleteTarget) return
    const authToken = getToken()
    if (!authToken) return

    setDeleting(true)
    try {
      const res = await fetch(`/api/v1/chat/conversations/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!res.ok) {
        throw new Error(`Delete failed (${res.status})`)
      }

      setConversations((prev) => prev.filter((conv) => conv.id !== deleteTarget.id))
      if (activeConversationId === deleteTarget.id) {
        startNewChat()
      }
      toast.success('Conversation deleted')
      setDeleteTarget(null)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete conversation'
      toast.error(msg)
    } finally {
      setDeleting(false)
    }
  }, [activeConversationId, deleteTarget, getToken, startNewChat])

  useEffect(() => {
    if (!isAuthenticated) return
    fetchConversations(1, false)
  }, [fetchConversations, isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated || loadingConversations || initialConversationHydratedRef.current) return

    if (conversationFromUrl) {
      const found = conversations.find((conversation) => conversation.id === conversationFromUrl)
      if (found) {
        openConversation(found)
      } else {
        fetchConversationById(conversationFromUrl).then((fetched) => {
          if (fetched) {
            openConversation(fetched)
          } else {
            toast.error('Conversation not found. Opening a new chat.')
            startNewChat()
          }
        })
      }
      initialConversationHydratedRef.current = true
      return
    }

    if (!activeConversationId && conversations.length > 0) {
      openConversation(conversations[0])
    }

    initialConversationHydratedRef.current = true
  }, [
    activeConversationId,
    conversations,
    isAuthenticated,
    loadingConversations,
    openConversation,
    conversationFromUrl,
    fetchConversationById,
    startNewChat,
  ])

  useEffect(() => {
    if (!isAuthenticated || loadingConversations) return

    if (!conversationFromUrl || conversationFromUrl === activeConversationId) return

    const found = conversations.find((conversation) => conversation.id === conversationFromUrl)
    if (found) {
      openConversation(found)
      return
    }
    fetchConversationById(conversationFromUrl).then((fetched) => {
      if (fetched) openConversation(fetched)
    })
  }, [
    activeConversationId,
    conversations,
    isAuthenticated,
    loadingConversations,
    openConversation,
    conversationFromUrl,
    fetchConversationById,
  ])

  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages, scrollToBottom])

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <>
      <div className="h-[calc(100vh-112px)] overflow-hidden rounded-2xl border border-border/70 bg-gradient-to-br from-background via-background to-secondary/40">
        <div className="flex h-full">
          <aside
            className={cn(
              'border-r border-border/70 bg-card/60 backdrop-blur-xl transition-all duration-300',
              sidebarOpen ? 'w-[320px]' : 'w-0 overflow-hidden'
            )}
          >
            <div className="flex h-full flex-col">
              <div className="border-b border-border/70 p-3">
                <Button className="w-full" onClick={startNewChat}>
                  <MessageSquarePlus className="mr-2 h-4 w-4" />
                  New Conversation
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto p-2">
                {loadingConversations ? (
                  <div className="grid place-items-center py-8 text-sm text-muted-foreground">
                    <Loader2 className="mb-2 h-4 w-4 animate-spin" />
                    Loading conversations...
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No conversations yet.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {conversations.map((conversation) => (
                      <button
                        key={conversation.id}
                        onClick={() => openConversation(conversation)}
                        className={cn(
                          'group w-full rounded-xl border p-3 text-left transition',
                          activeConversationId === conversation.id
                            ? 'border-primary/40 bg-primary/10'
                            : 'border-border/60 bg-background/60 hover:bg-secondary/50'
                        )}
                        title={conversation.title || 'Untitled conversation'}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="line-clamp-1 text-sm font-medium">
                            {conversation.title || 'Untitled conversation'}
                          </p>
                          <button
                            className="rounded-md p-1 opacity-0 transition hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                            onClick={(event) => {
                              event.stopPropagation()
                              setDeleteTarget(conversation)
                            }}
                            aria-label="Delete conversation"
                            type="button"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{conversation.message_count} msgs</span>
                          <span>•</span>
                          <span>{formatDistanceToNow(new Date(conversation.created_at), { addSuffix: true })}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {hasMoreConversations && (
                <div className="border-t border-border/70 p-2">
                  <Button
                    variant="ghost"
                    className="w-full"
                    onClick={() => fetchConversations(convPage + 1, true)}
                  >
                    Load more
                  </Button>
                </div>
              )}
            </div>
          </aside>

          <section className="flex min-w-0 flex-1 flex-col">
            <header className="flex items-center gap-3 border-b border-border/70 bg-background/70 p-4 backdrop-blur">
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setSidebarOpen((prev) => !prev)}
                aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              >
                {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>

              <div className="flex min-w-0 flex-1 items-center gap-2">
                {whiteLabelSettings.logo_url ? (
                  <img src={whiteLabelSettings.logo_url} alt="Logo" className="h-6 w-6 rounded" />
                ) : (
                  <Sparkles className="h-5 w-5 text-primary" />
                )}
                <h1 className="truncate text-sm font-semibold sm:text-base">{whiteLabelSettings.brand_name} AI Assistant</h1>
                <Badge variant={sending ? 'warning' : 'success'}>{sending ? 'Streaming...' : 'Ready'}</Badge>
              </div>
            </header>

            <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4">
              <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
                {olderMessagesPage ? (
                  <div className="flex justify-center">
                    <Button variant="outline" size="sm" onClick={loadOlderMessages} disabled={loadingMessages}>
                      {loadingMessages ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Load older messages
                    </Button>
                  </div>
                ) : null}

                {messages.length === 0 ? (
                  <Card className="border-dashed bg-card/50">
                    <CardHeader>
                      <CardTitle className="text-lg">How can I help today?</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                      <p>Ask questions, analyze knowledge, and stream responses in real time.</p>
                      <p>Links in responses are clickable, and reference sources appear as chips.</p>
                    </CardContent>
                  </Card>
                ) : (
                  messages.map((message) => {
                    const isAssistant = message.role === 'assistant'
                    const sources = isAssistant ? extractSourceLinks(message) : []
                    return (
                      <div
                        key={message.id}
                        className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
                      >
                        <div
                          className={cn(
                            'max-w-[85%] rounded-2xl border p-3 sm:max-w-[80%]',
                            message.role === 'user'
                              ? 'border-primary/30 bg-primary/10'
                              : 'border-border/70 bg-card/70'
                          )}
                        >
                          <div className="mb-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                            {message.role === 'user' ? (
                              <>
                                <UserRound className="h-3.5 w-3.5" />
                                You
                              </>
                            ) : (
                              <>
                                <Bot className="h-3.5 w-3.5" />
                                Assistant
                              </>
                            )}
                            {message.isStreaming ? (
                              <Badge variant="warning" className="ml-1">
                                Typing...
                              </Badge>
                            ) : null}
                          </div>

                          <div className="text-sm leading-relaxed">
                            <LinkifiedText text={message.content || ''} />
                          </div>

                          {sources.length > 0 ? (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {sources.map((source) => (
                                <a key={`${message.id}-${source.url}`} href={source.url} target="_blank" rel="noreferrer">
                                  <Badge variant="outline" className="gap-1 hover:bg-accent">
                                    <LinkIcon className="h-3 w-3" />
                                    {source.label}
                                  </Badge>
                                </a>
                              ))}
                            </div>
                          ) : null}

                          {(message.model_used || message.tokens_used || message.latency_ms) && (
                            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                              {message.model_used ? <Badge variant="secondary">{message.model_used}</Badge> : null}
                              {message.tokens_used ? <Badge variant="secondary">{message.tokens_used} tokens</Badge> : null}
                              {message.latency_ms ? <Badge variant="secondary">{message.latency_ms} ms</Badge> : null}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })
                )}
                <div ref={scrollAnchorRef} />
              </div>
            </div>

            <footer className="border-t border-border/70 bg-background/80 p-4 backdrop-blur">
              <div className="mx-auto grid w-full max-w-4xl gap-3">
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <label className="inline-flex items-center gap-2">
                    <Switch checked={useKnowledge} onCheckedChange={setUseKnowledge} />
                    Use knowledge
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <Switch checked={useMemory} onCheckedChange={setUseMemory} />
                    Use memory
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <Switch checked={toolsEnabled} onCheckedChange={setToolsEnabled} />
                    Tools enabled
                  </label>
                </div>

                <div className="relative">
                  <Textarea
                    value={composer}
                    onChange={(event) => setComposer(event.target.value)}
                    placeholder="Message your AI assistant..."
                    className="min-h-[88px] resize-none pr-14"
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        sendMessage()
                      }
                    }}
                    disabled={sending}
                  />
                  <Button
                    size="icon"
                    className="absolute bottom-3 right-3"
                    onClick={sendMessage}
                    disabled={sending || !composer.trim()}
                    aria-label="Send message"
                  >
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
                  </Button>
                </div>

                {error ? (
                  <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </div>
                ) : null}

                <div className="text-xs text-muted-foreground">
                  Session: <span className="font-mono">{activeSessionId}</span>
                </div>
              </div>
            </footer>
          </section>
        </div>
      </div>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => (!open ? setDeleteTarget(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the conversation and all messages. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={confirmDeleteConversation}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
