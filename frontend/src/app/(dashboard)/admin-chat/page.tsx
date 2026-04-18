'use client'

import { useEffect, useRef, useState } from 'react'
import { useSettings } from '@/lib/settings-context'
import { useAuth } from '@/lib/auth-context'
import { Bot, MessageSquarePlus, Send, Sparkles, Database } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  model_used?: string
  tokens_used?: number
  latency_ms?: number
  isStreaming?: boolean
}

interface Conversation {
  id: string
  session_id: string
  title: string | null
  message_count: number
  created_at: string
}

export default function AdminChatPage() {
  const settings = useSettings()
  const { token, isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string>('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingConvos, setLoadingConvos] = useState(true)
  const [useKnowledge, setUseKnowledge] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (isAuthenticated && token) fetchConversations()
  }, [isAuthenticated, token])

  const fetchConversations = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) {
      setError('Not authenticated. Please log in.')
      return
    }

    setLoadingConvos(true)
    try {
      const res = await fetch('/api/v1/chat/conversations?page=1&page_size=50', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        const convos = data.items || []
        setConversations(convos)
        if (convos.length > 0 && !currentConversationId) {
          setCurrentConversationId(convos[0].id)
          loadMessages(convos[0].id)
        }
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch {
      setError('Failed to load conversations')
    } finally {
      setLoadingConvos(false)
    }
  }

  const loadMessages = async (convId: string) => {
    const authToken = token || localStorage.getItem('access_token')
    if (!authToken) return

    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=100`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        const msgs = data.items || []
        setMessages(
          msgs.map((m: any) => ({
            id: m.id,
            role: m.role === 'user' ? 'user' : 'assistant',
            content: m.content || '',
            timestamp: m.created_at,
            model_used: m.model_used,
            tokens_used: m.tokens_used,
            latency_ms: m.latency_ms,
          }))
        )
        setError(null)
      }
    } catch {
      // no-op
    }
  }

  const handleSelectConversation = (convId: string) => {
    setCurrentConversationId(convId)
    loadMessages(convId)
  }

  const handleSendMessage = async () => {
    const authToken = token || localStorage.getItem('access_token')
    if (!input.trim() || loading || !authToken) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    const assistantMessageId = (Date.now() + 1).toString()
    const streamingMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    setMessages((prev) => [...prev, streamingMessage])

    try {
      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          use_knowledge: useKnowledge,
          session_id: currentConversationId || 'admin-chat-new',
        }),
      })

      if (!res.ok) {
        if (res.status === 401) {
          setError('Session expired. Please refresh.')
          setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId))
          return
        }
        throw new Error(`Stream failed: ${res.status}`)
      }

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let tokenCount = 0
      let latencyMs = 0
      let modelUsed = 'mistral:latest'

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const json = JSON.parse(line.slice(6))
            if (json.event === 'delta' && json.text) {
              fullContent += json.text
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMessageId ? { ...m, content: fullContent } : m))
              )
            } else if (json.event === 'done') {
              tokenCount = json.tokens_used || 0
              latencyMs = json.latency_ms || 0
              modelUsed = json.model_used || 'mistral:latest'
            }
          } catch {
            // ignore parse issues
          }
        }
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                isStreaming: false,
                tokens_used: tokenCount,
                latency_ms: latencyMs,
                model_used: modelUsed,
              }
            : m
        )
      )

      await fetchConversations()
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Unknown error'
      setError(errorMsg)
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId))
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: `Error: ${errorMsg}`,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setCurrentConversationId('')
    setMessages([])
  }

  if (!isAuthenticated) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Initializing authentication...</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card className="min-h-[680px]">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            {settings.logo_url ? <img src={settings.logo_url} alt="Logo" className="h-5 w-5 rounded" /> : null}
            <CardTitle className="text-base" style={{ color: settings.brand_color || undefined }}>
              {settings.brand_name}
            </CardTitle>
          </div>
          <CardDescription>Conversation sessions</CardDescription>
          <Button size="sm" onClick={handleNewChat}>
            <MessageSquarePlus className="mr-1.5 h-4 w-4" />
            New Chat
          </Button>
        </CardHeader>
        <CardContent>
          {loadingConvos ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground">No conversations yet.</p>
          ) : (
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    currentConversationId === conv.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border/70 hover:bg-secondary/30'
                  }`}
                >
                  <p className="truncate text-sm font-medium">{conv.title || 'Untitled'}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{new Date(conv.created_at).toLocaleDateString()}</p>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="min-h-[680px]">
        <CardHeader className="border-b border-border/70 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Bot className="h-4 w-4 text-primary" />
              Admin Chat
            </CardTitle>
            <Badge variant={token ? 'success' : 'warning'}>{token ? 'Authenticated' : 'No token'}</Badge>
          </div>
          <CardDescription>Live streaming responses from your backend route.</CardDescription>
          <label className="flex items-center gap-2 text-sm">
            <Switch checked={useKnowledge} onCheckedChange={setUseKnowledge} />
            <Database className="h-4 w-4 text-muted-foreground" />
            Use Knowledge Base
          </label>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </CardHeader>

        <CardContent className="flex h-[560px] flex-col p-0">
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Sparkles className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-2 text-sm text-muted-foreground">Start a conversation to begin streaming output.</p>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] rounded-xl border px-3 py-2 text-sm ${
                      msg.role === 'user'
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-border/70 bg-secondary/30'
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    {msg.role === 'assistant' && (
                      <p className="mt-2 text-xs opacity-80">
                        {msg.model_used || 'mistral:latest'}
                        {msg.tokens_used ? ` • ${msg.tokens_used} tokens` : ''}
                        {msg.latency_ms ? ` • ${msg.latency_ms}ms` : ''}
                        {msg.isStreaming ? ' • streaming...' : ''}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-border/70 p-3">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                placeholder="Type your message..."
                disabled={loading || !token}
              />
              <Button onClick={handleSendMessage} disabled={loading || !input.trim() || !token}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
