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
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Professional Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-5 flex justify-between items-center shadow-lg border-b border-blue-500">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span className="text-3xl">🤖</span>
            Admin Chat Agent
          </h1>
          <p className="text-sm text-blue-100 mt-1">Enterprise-grade AI assistant with knowledge integration</p>
        </div>
        <div className="flex items-center gap-3">
          {modelInfo.model && (
            <div className="text-right bg-blue-500 bg-opacity-20 backdrop-blur-sm px-4 py-3 rounded-lg border border-blue-400 border-opacity-30">
              <p className="text-xs text-blue-200">Model</p>
              <p className="text-sm font-mono font-semibold text-blue-100">
                {modelInfo.provider}/{modelInfo.model}
              </p>
            </div>
          )}
          <button
            onClick={handleNewChat}
            className="px-4 py-2 bg-white hover:bg-gray-100 text-blue-700 rounded-lg transition font-medium shadow-md"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-3xl">
                <div className="text-7xl mb-6 animate-pulse">🚀</div>
                <h2 className="text-4xl font-bold text-white mb-3">Welcome to Admin Chat</h2>
                <p className="text-lg text-gray-300 mb-8">
                  Enterprise-grade AI assistant with advanced reasoning, knowledge integration, and tool capabilities
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
                  <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-6 border border-purple-400 border-opacity-30">
                    <p className="text-2xl mb-3">🧠</p>
                    <p className="text-sm font-semibold text-white">Smart Reasoning</p>
                    <p className="text-xs text-purple-100 mt-1">Advanced agent-powered responses</p>
                  </div>
                  <div className="bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-lg p-6 border border-cyan-400 border-opacity-30">
                    <p className="text-2xl mb-3">📚</p>
                    <p className="text-sm font-semibold text-white">Knowledge Base</p>
                    <p className="text-xs text-cyan-100 mt-1">Context-aware answers</p>
                  </div>
                  <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg p-6 border border-emerald-400 border-opacity-30">
                    <p className="text-2xl mb-3">🔧</p>
                    <p className="text-sm font-semibold text-white">Tool Use</p>
                    <p className="text-xs text-emerald-100 mt-1">Extended capabilities</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl ${
                    msg.role === 'user'
                      ? 'px-5 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-2xl rounded-br-none shadow-lg border border-blue-500'
                      : msg.error
                      ? 'w-full px-5 py-3 bg-red-900 text-red-100 border-l-4 border-red-500 rounded-lg rounded-bl-none shadow-lg'
                      : 'w-full'
                  }`}>
                    {msg.role === 'user' ? (
                      <>
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                        <div className="flex gap-3 mt-2 text-xs text-blue-100">
                          <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </>
                    ) : (
                      <div className="bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-600 rounded-lg rounded-bl-none space-y-3 shadow-lg">
                        {/* Main response */}
                        <div className="px-5 pt-4">
                          <p className="whitespace-pre-wrap text-sm text-gray-100 leading-relaxed">{msg.content}</p>
                        </div>

                        {/* Tool calls if present */}
                        {msg.tool_calls && msg.tool_calls.length > 0 && (
                          <div className="px-5 py-3 bg-amber-900 bg-opacity-30 border-t border-slate-600">
                            <p className="text-xs font-semibold text-amber-300 mb-2">🔧 Agent Actions:</p>
                            {msg.tool_calls.map((tool, idx) => (
                              <div key={idx} className="text-xs text-amber-200 mb-1">
                                <span className="font-mono bg-amber-800 bg-opacity-50 px-2 py-1 rounded">{tool.name}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Knowledge base usage */}
                        {(msg.knowledge_chunks_used || msg.memory_items_used) && (
                          <div className="px-5 py-3 bg-cyan-900 bg-opacity-30 border-t border-slate-600">
                            <p className="text-xs font-semibold text-cyan-300 mb-2">📚 Context Sources:</p>
                            <div className="text-xs text-cyan-200 space-y-1">
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
                        <div className="px-5 pb-4 pt-2 border-t border-slate-600 flex gap-4 flex-wrap text-xs text-gray-400">
                          {msg.timestamp && (
                            <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                          )}
                          {msg.model_used && (
                            <span className="font-mono text-gray-300">Model: {msg.model_used}</span>
                          )}
                          {msg.tokens_used && (
                            <span>📊 {msg.tokens_used} tokens</span>
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
                  <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-gray-100 px-5 py-3 rounded-lg rounded-bl-none border border-slate-600 shadow-lg">
                    <div className="flex gap-2 items-center">
                      <div className="animate-spin text-lg">⏳</div>
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
        <div className="bg-gradient-to-b from-slate-800 to-slate-900 border-t border-slate-700 px-6 py-4 shadow-lg">
          <div className="max-w-4xl mx-auto space-y-3">
            <div className="flex gap-2 items-center">
              <label className="flex items-center gap-2 text-sm cursor-pointer flex-shrink-0 bg-slate-700 hover:bg-slate-600 px-3 py-2 rounded-lg transition">
                <input
                  type="checkbox"
                  checked={useKnowledge}
                  onChange={(e) => setUseKnowledge(e.target.checked)}
                  className="w-4 h-4 rounded"
                  disabled={loading}
                />
                <span className="text-gray-300">📚 Use Knowledge Base</span>
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
                placeholder="Ask me anything... (Shift+Enter for new line)"
                className="flex-1 px-5 py-3 bg-slate-700 border border-slate-600 text-white placeholder-gray-400 rounded-lg disabled:bg-slate-800 disabled:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-600 disabled:to-gray-700 text-white rounded-lg font-medium transition shadow-lg border border-blue-500"
              >
                {loading ? '⏳' : '➤'}
              </button>
            </div>

            <p className="text-xs text-gray-500 text-center">
              Powered by advanced AI agent with knowledge base, memory, and tool integration
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
