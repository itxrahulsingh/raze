'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  model_used?: string
  tokens_used?: number
  latency_ms?: number
}

interface Conversation {
  id: string
  title: string | null
  message_count: number
  created_at: string
}

export default function AdminChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentConvId, setCurrentConvId] = useState<string>('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversationsLoading, setConversationsLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  // Get token from localStorage immediately (no wait for AuthContext)
  const getToken = useCallback(() => {
    return localStorage.getItem('access_token')
  }, [])

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchConversations = async (pageNum = 1) => {
    const token = getToken()
    if (!token) return

    try {
      const res = await fetch(`/api/v1/chat/conversations?page=${pageNum}&page_size=15`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        const newConvos = data.items || []

        if (pageNum === 1) {
          setConversations(newConvos)
        } else {
          setConversations(prev => [...prev, ...newConvos])
        }

        setHasMore((data.items || []).length > 0)
        setPage(pageNum)
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    } finally {
      if (pageNum === 1) setConversationsLoading(false)
    }
  }

  const loadMessages = async (convId: string) => {
    const token = getToken()
    if (!token) return

    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data.items || [])
        setError(null)
      }
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }

  const sendMessage = async () => {
    const token = getToken()
    if (!input.trim() || !token || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    const assistantId = (Date.now() + 1).toString()
    let fullContent = ''

    try {
      // Use current conversation ID if exists, otherwise create new
      const sessionId = currentConvId || `new-${Date.now()}`

      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId
        })
      })

      if (!res.ok) {
        throw new Error(`Chat failed: ${res.status}`)
      }

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      setMessages(prev => [...prev, {
        id: assistantId,
        role: 'assistant',
        content: '...',
        timestamp: new Date().toISOString()
      }])

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
                fullContent += json.text
                setMessages(prev => prev.map(m =>
                  m.id === assistantId ? { ...m, content: fullContent } : m
                ))
              }
            } catch (e) {
              // Ignore
            }
          }
        }
      }

      // Refresh conversations to get new title if it's a new chat
      await fetchConversations()
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Unknown error'
      setError(errorMsg)
      setMessages(prev => prev.filter(m => m.id !== assistantId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex bg-white text-gray-900">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-gray-100 border-r border-gray-200 flex flex-col transition-all overflow-hidden`}>
        <div className="p-4 border-b border-gray-200">
          <Button
            onClick={() => { setCurrentConvId(''); setMessages([]); }}
            className="w-full bg-gray-800 hover:bg-gray-700 text-white"
          >
            + New chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversationsLoading ? (
            <div className="p-4 text-sm text-gray-500">Loading...</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-sm text-gray-500">No conversations</div>
          ) : (
            <div className="space-y-1 p-2">
              {conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => { setCurrentConvId(conv.id); loadMessages(conv.id); }}
                  className={`w-full text-left px-3 py-2 rounded text-sm hover:bg-gray-200 transition truncate ${
                    currentConvId === conv.id ? 'bg-gray-300' : ''
                  }`}
                  title={conv.title || 'New chat'}
                >
                  {conv.title || 'New chat'}
                </button>
              ))}

              {hasMore && (
                <button
                  onClick={() => fetchConversations(page + 1)}
                  className="w-full text-left px-3 py-2 text-xs text-gray-500 hover:text-gray-700 transition"
                >
                  ↓ Load more
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 p-4 flex items-center gap-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded"
          >
            {sidebarOpen ? '←' : '→'}
          </button>
          <h1 className="text-lg font-semibold">ChatGPT</h1>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-5xl mb-4">ChatGPT</div>
                <p className="text-2xl font-semibold mb-2">How can I help you today?</p>
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl ${
                msg.role === 'user'
                  ? 'bg-gray-200 text-gray-900 rounded-lg px-4 py-2'
                  : 'text-gray-900 px-4 py-2'
              }`}>
                <p className="whitespace-pre-wrap break-words text-sm">{msg.content || '...'}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-white">
          {error && (
            <div className="mb-3 p-3 bg-red-100 border border-red-300 rounded text-sm text-red-700">
              ❌ {error}
            </div>
          )}
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder="Message ChatGPT..."
              disabled={loading}
              className="flex-1 bg-gray-100 border-gray-300 text-gray-900 placeholder-gray-500"
            />
            <Button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-gray-800 hover:bg-gray-700 text-white"
            >
              {loading ? '⏳' : '→'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
