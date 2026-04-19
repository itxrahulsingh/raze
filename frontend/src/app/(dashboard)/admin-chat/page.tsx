'use client'
import { useEffect, useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { useAuth } from '@/lib/auth-context'

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
  const { token, isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentConvId, setCurrentConvId] = useState<string>('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const authToken = token || localStorage.getItem('access_token')

  useEffect(() => {
    if (authToken) {
      fetchConversations()
    }
  }, [authToken])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/v1/chat/conversations?page=1&page_size=20', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        const convos = data.items || []
        setConversations(convos)
        if (!currentConvId && convos.length > 0) {
          setCurrentConvId(convos[0].id)
          loadMessages(convos[0].id)
        }
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    }
  }

  const loadMessages = async (convId: string) => {
    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=100`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
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
    if (!input.trim() || !authToken || loading) return

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
      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: currentConvId || 'new-chat'
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
        content: '',
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
              // Ignore parse errors
            }
          }
        }
      }

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
    <div className="h-screen flex bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <Button onClick={() => { setCurrentConvId(''); setMessages([]); }} className="w-full bg-blue-600 hover:bg-blue-700">
            + New Chat
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => { setCurrentConvId(conv.id); loadMessages(conv.id); }}
              className={`w-full text-left px-4 py-3 border-b border-gray-800 hover:bg-gray-800 transition ${
                currentConvId === conv.id ? 'bg-gray-800' : ''
              }`}
            >
              <div className="text-sm font-medium truncate">{conv.title || 'New Chat'}</div>
              <div className="text-xs text-gray-500">{conv.message_count} messages</div>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-6xl mb-4">💬</div>
                <p className="text-xl font-medium mb-2">Start a conversation</p>
                <p className="text-gray-400">Send a message to begin</p>
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <Card className={`max-w-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-gray-800 border-gray-700'
              }`}>
                <p className="text-sm whitespace-pre-wrap break-words">{msg.content || '...'}</p>
                {msg.role === 'assistant' && msg.model_used && (
                  <div className="mt-2 pt-2 border-t border-gray-700 text-xs text-gray-400 space-x-3">
                    <span>🤖 {msg.model_used}</span>
                    {msg.tokens_used && <span>📊 {msg.tokens_used} tokens</span>}
                    {msg.latency_ms && <span>⚡ {msg.latency_ms}ms</span>}
                  </div>
                )}
              </Card>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 p-4 bg-gray-950">
          {error && (
            <div className="mb-3 p-3 bg-red-900 border border-red-700 rounded text-sm text-red-200">
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
              placeholder="Type your message..."
              disabled={loading || !authToken}
              className="flex-1 bg-gray-800 border-gray-700 text-white placeholder-gray-500"
            />
            <Button
              onClick={sendMessage}
              disabled={loading || !input.trim() || !authToken}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? '⏳' : 'Send'}
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {authToken ? '✅ Connected' : '❌ Not authenticated'}
          </p>
        </div>
      </div>
    </div>
  )
}
