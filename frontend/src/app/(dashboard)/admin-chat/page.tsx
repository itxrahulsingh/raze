'use client'
import { useEffect, useState, useRef } from 'react'
import { useSettings } from '@/lib/settings-context'
import { useAuth } from '@/lib/auth-context'

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

  // Load conversation history when auth is ready
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchConversations()
    }
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
        headers: { 'Authorization': `Bearer ${authToken}` }
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
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
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
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        const msgs = data.items || []
        setMessages(msgs.map((m: any) => ({
          id: m.id,
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content || '',
          timestamp: m.created_at,
          model_used: m.model_used,
          tokens_used: m.tokens_used,
          latency_ms: m.latency_ms,
        })))
        setError(null)
      }
    } catch (e) {
      console.error('Failed to load messages:', e)
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

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    // Create streaming message placeholder
    const assistantMessageId = (Date.now() + 1).toString()
    const streamingMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    setMessages(prev => [...prev, streamingMessage])

    try {
      const startTime = Date.now()

      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          use_knowledge: useKnowledge,
          session_id: currentConversationId || 'admin-chat-new',
        })
      })

      if (!res.ok) {
        if (res.status === 401) {
          setError('Session expired. Please refresh.')
          setMessages(prev => prev.filter(m => m.id !== assistantMessageId))
          return
        }
        throw new Error(`Stream failed: ${res.status}`)
      }

      if (!res.body) {
        throw new Error('No response body')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let tokenCount = 0
      let latencyMs = 0
      let modelUsed = 'mistral:latest'

      let isFirstChunk = true
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const json = JSON.parse(line.slice(6))

              if (json.event === 'delta' && json.text) {
                isFirstChunk = false
                fullContent += json.text
                // Update message in REAL-TIME (word by word)
                setMessages(prev => prev.map(m =>
                  m.id === assistantMessageId
                    ? { ...m, content: fullContent }
                    : m
                ))
              } else if (json.event === 'done') {
                tokenCount = json.tokens_used || 0
                latencyMs = json.latency_ms || 0
                modelUsed = json.model_used || 'mistral:latest'
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      // Update final message with metadata
      setMessages(prev => prev.map(m =>
        m.id === assistantMessageId
          ? {
              ...m,
              isStreaming: false,
              tokens_used: tokenCount,
              latency_ms: latencyMs,
              model_used: modelUsed,
            }
          : m
      ))

      // Refresh conversations
      await fetchConversations()
    } catch (e) {
      console.error('Failed to send message:', e)
      const errorMsg = e instanceof Error ? e.message : 'Unknown error'
      setError(errorMsg)
      setMessages(prev => prev.filter(m => m.id !== assistantMessageId))
      setMessages(prev => [...prev, {
        id: assistantMessageId,
        role: 'assistant',
        content: `❌ Error: ${errorMsg}`,
        timestamp: new Date().toISOString(),
      }])
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
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-lg text-gray-600 mb-4">Loading...</p>
          <p className="text-sm text-gray-400">Please wait while authentication initializes</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex bg-white rounded-lg shadow overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-200 flex flex-col bg-gradient-to-b from-slate-50 to-gray-50">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-4">
            {settings.logo_url && <img src={settings.logo_url} alt="Logo" className="w-6 h-6" />}
            <h1 className="text-lg font-bold" style={{ color: settings.brand_color }}>
              {settings.brand_name}
            </h1>
          </div>
          <button
            onClick={handleNewChat}
            className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
          >
            + New Chat
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {loadingConvos ? (
            <div className="p-4 text-center text-gray-500 text-sm">Loading...</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">No conversations yet</div>
          ) : (
            <div className="space-y-1 p-2">
              {conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                    currentConversationId === conv.id
                      ? 'bg-white shadow text-slate-900 font-medium'
                      : 'text-gray-700 hover:bg-white/50'
                  }`}
                >
                  <div className="truncate font-medium">{conv.title || 'Untitled'}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(conv.created_at).toLocaleDateString()}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border-b border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <div className="text-5xl mb-4">💬</div>
                <p className="text-lg font-medium mb-2">Start a conversation</p>
                <p className="text-sm">Send a message to begin. Streaming will appear word-by-word →</p>
              </div>
            </div>
          )}
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-2xl px-4 py-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-white text-gray-900 border border-gray-200 rounded-bl-none'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                {msg.role === 'assistant' && (
                  <div className="mt-2 pt-2 border-t border-gray-200 flex items-center gap-3 text-xs text-gray-600">
                    <span>🤖 {msg.model_used || 'mistral:latest'}</span>
                    {msg.tokens_used && <span>📊 {msg.tokens_used} tokens</span>}
                    {msg.latency_ms && <span>⚡ {msg.latency_ms}ms</span>}
                    {msg.isStreaming && <span className="animate-pulse">🔄 Streaming...</span>}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="flex gap-2 mb-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={useKnowledge}
                onChange={(e) => setUseKnowledge(e.target.checked)}
                className="rounded"
              />
              <span>Use Knowledge Base</span>
            </label>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage()
                }
              }}
              placeholder="Type your message... (Shift+Enter for newline)"
              disabled={loading || !token}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim() || !token}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? '⏳' : '→'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {token ? '✅ Authenticated - Token auto-refreshes' : '❌ Not authenticated'}
          </p>
        </div>
      </div>
    </div>
  )
}
