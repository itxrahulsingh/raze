'use client'
import { useEffect, useState, useRef } from 'react'

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
  session_id: string
  title: string
  message_count: number
  created_at: string
}

export default function AdminChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string>('')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingConvos, setLoadingConvos] = useState(true)
  const [useKnowledge, setUseKnowledge] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load conversation history
  useEffect(() => {
    fetchConversations()
  }, [])

  const fetchConversations = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat/conversations?limit=50', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        const convos = data.items || []
        setConversations(convos)
        if (convos.length > 0 && !currentConversationId) {
          setCurrentConversationId(convos[0].id)
          loadMessages(convos[0].id)
        }
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    } finally {
      setLoadingConvos(false)
    }
  }

  const loadMessages = async (convId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        const msgs = data.items || []
        setMessages(msgs.map((m: any) => ({
          id: m.id,
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content,
          timestamp: m.created_at,
          model_used: m.model_used,
          tokens_used: m.tokens_used,
          latency_ms: m.latency_ms,
        })))
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
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const token = localStorage.getItem('access_token')
      const startTime = Date.now()
      
      const res = await fetch('/api/v1/chat/message', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          use_knowledge: useKnowledge,
          session_id: currentConversationId || 'admin-chat-new',
        })
      })

      if (res.ok) {
        const data = await res.json()
        const latency = Date.now() - startTime
        
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.content || 'No response',
          timestamp: new Date().toISOString(),
          model_used: data.model_used,
          tokens_used: data.tokens_used,
          latency_ms: latency,
        }
        setMessages(prev => [...prev, assistantMessage])
        
        // Refresh conversations to show updated list
        if (!currentConversationId) {
          await fetchConversations()
        }
      } else {
        const errorData = await res.json().catch(() => ({ detail: 'Failed to get response' }))
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: `❌ Error: ${errorData.detail}`,
          timestamp: new Date().toISOString(),
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (e) {
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: `❌ Connection error: ${String(e)}`,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setCurrentConversationId('')
    setMessages([])
    setInput('')
    fetchConversations()
  }

  return (
    <div className="h-screen flex bg-white">
      {/* Sidebar - Conversation History (ChatGPT Style) */}
      <div className="w-64 bg-gray-900 text-white flex flex-col border-r border-gray-700 shadow-lg">
        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className="m-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition"
        >
          + New Chat
        </button>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-2">
          {loadingConvos ? (
            <div className="text-gray-400 text-sm p-4">Loading conversations...</div>
          ) : conversations.length === 0 ? (
            <div className="text-gray-400 text-sm p-4">No conversations yet</div>
          ) : (
            conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => handleSelectConversation(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition truncate ${
                  currentConversationId === conv.id
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`}
                title={conv.title}
              >
                {conv.title || `Chat ${new Date(conv.created_at).toLocaleDateString()}`}
              </button>
            ))
          )}
        </div>

        {/* Settings Link */}
        <div className="p-4 border-t border-gray-700">
          <a href="/settings" className="text-gray-400 hover:text-white text-sm">
            ⚙️ Settings
          </a>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4 flex justify-between items-center bg-gradient-to-r from-blue-50 to-cyan-50">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Chat</h1>
            <p className="text-sm text-gray-600">Enterprise AI Assistant</p>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl">
                <div className="text-6xl mb-4">💬</div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Start a conversation</h2>
                <p className="text-gray-600">Ask anything and get instant AI-powered responses</p>
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl ${
                    msg.role === 'user'
                      ? 'px-4 py-3 bg-blue-600 text-white rounded-lg rounded-br-none shadow'
                      : 'w-full'
                  }`}>
                    {msg.role === 'user' ? (
                      <p className="text-sm">{msg.content}</p>
                    ) : (
                      <div className="bg-white border border-gray-200 rounded-lg rounded-bl-none shadow p-4">
                        <p className="text-sm text-gray-900 whitespace-pre-wrap">{msg.content}</p>
                        <div className="flex gap-4 mt-3 text-xs text-gray-500 flex-wrap">
                          {msg.model_used && <span>Model: {msg.model_used}</span>}
                          {msg.tokens_used && <span>Tokens: {msg.tokens_used}</span>}
                          {msg.latency_ms && <span>⚡ {msg.latency_ms}ms</span>}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="flex gap-2">
                      <div className="animate-spin">⏳</div>
                      <span className="text-sm">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 px-6 py-4 shadow-lg">
          <div className="max-w-4xl mx-auto space-y-3">
            <div className="flex gap-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={useKnowledge}
                  onChange={(e) => setUseKnowledge(e.target.checked)}
                  className="w-4 h-4 rounded"
                  disabled={loading}
                />
                <span className="text-gray-700">📚 Use Knowledge Base</span>
              </label>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                disabled={loading}
                placeholder="Ask anything... (Shift+Enter for new line)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg disabled:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
              >
                {loading ? '⏳' : '➤'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
