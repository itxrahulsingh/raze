'use client'
import { useEffect, useState, useRef } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: Array<{ name: string; type: string }>
}

export default function TestChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [aiStatus, setAiStatus] = useState<'checking' | 'ready' | 'error'>('checking')
  const [statusMessage, setStatusMessage] = useState('Checking AI status...')
  const [useKnowledge, setUseKnowledge] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    checkAIStatus()
  }, [])

  const checkAIStatus = async () => {
    try {
      const res = await fetch('/api/v1/health')
      if (res.ok) {
        const data = await res.json()
        if (data.status === 'healthy') {
          setAiStatus('ready')
          setStatusMessage('✅ AI System Ready')
        } else {
          setAiStatus('error')
          setStatusMessage('⚠️ System Degraded: ' + data.status)
        }
      }
    } catch (e) {
      setAiStatus('error')
      setStatusMessage('❌ Failed to connect to AI system')
    }
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
      const res = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          use_knowledge: useKnowledge,
          stream: false,
        })
      })

      if (res.ok) {
        const data = await res.json()
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || data.message || 'No response',
          timestamp: new Date().toISOString(),
          sources: data.sources || [],
        }
        setMessages(prev => [...prev, assistantMessage])
      } else if (res.status === 404) {
        // Fallback if endpoint doesn't exist - show demo response
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `I received your message: "${userMessage.content}"\n\nNote: Chat endpoint integration in progress. The AI configuration system is ready, but the chat API endpoint needs implementation.`,
          timestamp: new Date().toISOString(),
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        const error = await res.text()
        throw new Error(error || 'Failed to get response')
      }
    } catch (e) {
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: `❌ Error: ${String(e)}`,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Chat Test Interface</h1>
        <div className={`px-4 py-2 rounded-lg font-medium ${
          aiStatus === 'ready' ? 'bg-green-100 text-green-800' :
          aiStatus === 'error' ? 'bg-red-100 text-red-800' :
          'bg-yellow-100 text-yellow-800'
        }`}>
          {statusMessage}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Chat Area */}
        <div className="lg:col-span-3 bg-white rounded-lg shadow flex flex-col h-96">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <p className="text-lg font-medium">👋 Start a conversation</p>
                  <p className="text-sm mt-2">Ask me anything! I can answer from your knowledge base.</p>
                </div>
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-xs lg:max-w-md p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-gray-200 text-gray-900 rounded-bl-none'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-400 text-xs">
                        <p className="font-bold">📚 Sources:</p>
                        {msg.sources.map((src, idx) => (
                          <p key={idx}>• {src.name} ({src.type})</p>
                        ))}
                      </div>
                    )}
                    <p className="text-xs opacity-75 mt-1">{new Date(msg.timestamp).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-900 p-3 rounded-lg rounded-bl-none">
                  <p className="text-sm">⏳ AI is thinking...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t p-4 space-y-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={useKnowledge}
                onChange={(e) => setUseKnowledge(e.target.checked)}
                className="w-4 h-4"
              />
              <span>Use Knowledge Base</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                disabled={loading || aiStatus === 'error'}
                placeholder={aiStatus === 'error' ? 'AI system offline' : 'Type your message...'}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim() || aiStatus === 'error'}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? '⏳' : '➤'}
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-4">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h3 className="font-bold text-blue-900 mb-2">💡 Tips</h3>
            <ul className="text-sm text-blue-800 space-y-2">
              <li>• Ask questions about your knowledge base</li>
              <li>• Try: "What do you know about..."</li>
              <li>• Enable/disable knowledge base toggle</li>
              <li>• Check response sources below</li>
            </ul>
          </div>

          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h3 className="font-bold text-green-900 mb-2">✅ System Status</h3>
            <div className="text-sm text-green-800 space-y-1">
              <p>• AI Configuration: Ready</p>
              <p>• Knowledge Base: {useKnowledge ? 'Enabled' : 'Disabled'}</p>
              <p>• Streaming: Available</p>
              <p>• Tools: Available</p>
            </div>
          </div>

          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <h3 className="font-bold text-purple-900 mb-2">⚙️ Configuration</h3>
            <p className="text-sm text-purple-800 mb-3">
              Configure AI models, providers, and white label settings in Admin Settings.
            </p>
            <a
              href="/settings"
              className="text-sm text-purple-600 hover:text-purple-800 font-medium underline"
            >
              Go to Settings →
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
