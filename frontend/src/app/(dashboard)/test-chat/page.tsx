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
  error?: boolean
  tool_calls?: Array<{name: string; arguments: any}>
  tool_results?: Array<{tool: string; result: string}>
  knowledge_chunks_used?: number
  memory_items_used?: number
}

export default function AdminChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useKnowledge, setUseKnowledge] = useState(true)
  const [modelInfo, setModelInfo] = useState<{provider?: string; model?: string}>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
      const res = await fetch('/api/v1/chat/message', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          use_knowledge: useKnowledge,
          session_id: 'admin-chat',
        })
      })

      if (res.ok) {
        const data = await res.json()
        setModelInfo({
          provider: data.provider_used,
          model: data.model_used,
        })
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.content || 'No response',
          timestamp: new Date().toISOString(),
          model_used: data.model_used,
          tokens_used: data.tokens_used,
          latency_ms: data.latency_ms,
          tool_calls: data.tool_calls,
          tool_results: data.tool_results,
          knowledge_chunks_used: data.knowledge_chunks_used,
          memory_items_used: data.memory_items_used,
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }))
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: `❌ Error: ${errorData.detail || 'Failed to get response'}`,
          timestamp: new Date().toISOString(),
          error: true,
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (e) {
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: `❌ Connection error: ${String(e)}`,
        timestamp: new Date().toISOString(),
        error: true,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setInput('')
    setModelInfo({})
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Chat</h1>
          <p className="text-sm text-gray-600 mt-1">Full-featured AI agent chat with knowledge base integration</p>
        </div>
        <div className="flex items-center gap-3">
          {modelInfo.model && (
            <div className="text-right bg-blue-50 px-3 py-2 rounded-lg">
              <p className="text-xs text-blue-600">Using</p>
              <p className="text-sm font-mono font-semibold text-blue-900">
                {modelInfo.provider}/{modelInfo.model}
              </p>
            </div>
          )}
          <button
            onClick={handleNewChat}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-900 rounded-lg transition font-medium"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl">
                <div className="text-6xl mb-4">🤖</div>
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Admin Chat Agent</h2>
                <p className="text-lg text-gray-600 mb-4">
                  Enterprise-grade AI chat with knowledge base, memory, and tool integration
                </p>
                <div className="grid grid-cols-3 gap-4 mt-8">
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <p className="text-2xl mb-2">🧠</p>
                    <p className="text-sm font-semibold text-gray-900">Smart Reasoning</p>
                    <p className="text-xs text-gray-600">Agent-powered responses</p>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <p className="text-2xl mb-2">📚</p>
                    <p className="text-sm font-semibold text-gray-900">Knowledge Base</p>
                    <p className="text-xs text-gray-600">Context-aware answers</p>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <p className="text-2xl mb-2">🔧</p>
                    <p className="text-sm font-semibold text-gray-900">Tool Use</p>
                    <p className="text-xs text-gray-600">Extended capabilities</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl ${
                    msg.role === 'user'
                      ? 'px-4 py-3 bg-blue-600 text-white rounded-lg rounded-br-none'
                      : msg.error
                      ? 'w-full px-4 py-3 bg-red-50 text-red-900 border border-red-200 rounded-lg rounded-bl-none'
                      : 'w-full'
                  }`}>
                    {msg.role === 'user' ? (
                      <>
                        <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                        <div className="flex gap-3 mt-2 text-xs text-blue-100">
                          <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </>
                    ) : (
                      <div className="bg-white border border-gray-200 rounded-lg rounded-bl-none space-y-3">
                        {/* Main response */}
                        <div className="px-4 pt-3">
                          <p className="whitespace-pre-wrap text-sm text-gray-900">{msg.content}</p>
                        </div>

                        {/* Tool calls if present */}
                        {msg.tool_calls && msg.tool_calls.length > 0 && (
                          <div className="px-4 py-2 bg-amber-50 border-t border-gray-200">
                            <p className="text-xs font-semibold text-amber-900 mb-2">🔧 Agent Actions:</p>
                            {msg.tool_calls.map((tool, idx) => (
                              <div key={idx} className="text-xs text-amber-800 mb-1">
                                <span className="font-mono bg-amber-100 px-2 py-1 rounded">{tool.name}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Knowledge base usage */}
                        {(msg.knowledge_chunks_used || msg.memory_items_used) && (
                          <div className="px-4 py-2 bg-blue-50 border-t border-gray-200">
                            <p className="text-xs font-semibold text-blue-900 mb-1">📚 Context Sources:</p>
                            <div className="text-xs text-blue-800 space-y-1">
                              {msg.knowledge_chunks_used ? (
                                <p>• Knowledge: {msg.knowledge_chunks_used} chunk{msg.knowledge_chunks_used !== 1 ? 's' : ''}</p>
                              ) : null}
                              {msg.memory_items_used ? (
                                <p>• Memory: {msg.memory_items_used} item{msg.memory_items_used !== 1 ? 's' : ''}</p>
                              ) : null}
                            </div>
                          </div>
                        )}

                        {/* Response metrics */}
                        <div className="px-4 pb-3 pt-2 border-t border-gray-200 flex gap-4 flex-wrap text-xs text-gray-600">
                          {msg.timestamp && (
                            <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                          )}
                          {msg.model_used && (
                            <span className="font-mono">Model: {msg.model_used}</span>
                          )}
                          {msg.tokens_used && (
                            <span>Tokens: {msg.tokens_used}</span>
                          )}
                          {msg.latency_ms && (
                            <span>⚡ {msg.latency_ms}ms</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 text-gray-900 px-4 py-3 rounded-lg rounded-bl-none">
                    <div className="flex gap-2 items-center">
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
        <div className="bg-white border-t border-gray-200 px-6 py-4">
          <div className="max-w-4xl mx-auto space-y-3">
            <div className="flex gap-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer flex-shrink-0">
                <input
                  type="checkbox"
                  checked={useKnowledge}
                  onChange={(e) => setUseKnowledge(e.target.checked)}
                  className="w-4 h-4 rounded"
                  disabled={loading}
                />
                <span className="text-gray-700">Use Knowledge Base</span>
              </label>
            </div>

            <div className="flex gap-2">
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
                placeholder="Type your message (Shift+Enter for new line)..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg disabled:bg-gray-100 disabled:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition disabled:cursor-not-allowed"
              >
                {loading ? '⏳' : '➤'}
              </button>
            </div>

            <p className="text-xs text-gray-500 text-center">
              Powered by AI agent with knowledge base, memory, and tool integration
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
