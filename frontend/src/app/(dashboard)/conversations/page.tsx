'use client'
import { useEffect, useState } from 'react'

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
  conv_metadata?: {
    ip_address?: string
    country?: string
    city?: string
    user_agent?: string
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  model_used?: string
  tokens_used?: number
  latency_ms?: number
  created_at: string
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationDetail[]>([])
  const [selectedConvId, setSelectedConvId] = useState<string>('')
  const [selectedMessages, setSelectedMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [totalConversations, setTotalConversations] = useState(0)

  const itemsPerPage = 10

  useEffect(() => {
    fetchConversations(page)
  }, [page])

  const fetchConversations = async (pageNum: number) => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      
      const res = await fetch(`/api/v1/chat/conversations?page=${pageNum}&page_size=${itemsPerPage}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (res.ok) {
        const data = await res.json()
        setConversations(data.items || [])
        setTotalConversations(data.total || 0)
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    } finally {
      setLoading(false)
    }
  }

  const loadConversationMessages = async (convId: string) => {
    setLoadingMessages(true)
    setSelectedConvId(convId)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?page=1&page_size=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (res.ok) {
        const data = await res.json()
        setSelectedMessages(data.items || [])
      }
    } catch (e) {
      console.error('Failed to load messages:', e)
    } finally {
      setLoadingMessages(false)
    }
  }

  const deleteConversation = async (convId: string) => {
    if (!confirm('Delete this conversation?')) return
    
    try {
      const token = localStorage.getItem('access_token')
      await fetch(`/api/v1/chat/conversations/${convId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      fetchConversations(page)
      if (selectedConvId === convId) {
        setSelectedConvId('')
        setSelectedMessages([])
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  const filteredConversations = conversations.filter(c =>
    (c.title || 'Untitled').toLowerCase().includes(searchTerm.toLowerCase())
  )

  const totalPages = Math.ceil(totalConversations / itemsPerPage)
  const currentConv = conversations.find(c => c.id === selectedConvId)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Conversations</h1>
        <div className="text-sm text-gray-600">
          Total: {totalConversations} conversations
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Conversations List */}
        <div className="col-span-1 bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
          </div>

          <div className="space-y-1 max-h-screen overflow-y-auto">
            {loading ? (
              <div className="p-4 text-gray-500 text-sm">Loading...</div>
            ) : filteredConversations.length === 0 ? (
              <div className="p-4 text-gray-500 text-sm">No conversations found</div>
            ) : (
              filteredConversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => loadConversationMessages(conv.id)}
                  className={`w-full text-left px-4 py-3 text-sm border-b hover:bg-blue-50 transition ${
                    selectedConvId === conv.id ? 'bg-blue-100 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="font-medium truncate">{conv.title || 'Untitled'}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(conv.created_at).toLocaleDateString()} • {conv.message_count} messages
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t flex justify-between items-center">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="text-sm px-3 py-1 bg-gray-100 rounded disabled:opacity-50"
              >
                ← Prev
              </button>
              <span className="text-sm">{page} / {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="text-sm px-3 py-1 bg-gray-100 rounded disabled:opacity-50"
              >
                Next →
              </button>
            </div>
          )}
        </div>

        {/* Conversation Details & Messages */}
        <div className="col-span-2 bg-white rounded-lg shadow overflow-hidden flex flex-col">
          {selectedConvId && currentConv ? (
            <>
              {/* Header with Metadata */}
              <div className="p-6 border-b bg-gradient-to-r from-blue-50 to-cyan-50">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-bold">
                      {currentConv.title || 'Untitled Conversation'}
                    </h2>
                    <p className="text-sm text-gray-600 mt-1">
                      {new Date(currentConv.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteConversation(selectedConvId)}
                    className="px-3 py-2 bg-red-100 text-red-600 rounded hover:bg-red-200 text-sm"
                  >
                    🗑️ Delete
                  </button>
                </div>

                {/* Metadata Cards */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-white p-3 rounded border">
                    <div className="text-xs text-gray-500">Messages</div>
                    <div className="text-lg font-bold">{currentConv.message_count}</div>
                  </div>
                  <div className="bg-white p-3 rounded border">
                    <div className="text-xs text-gray-500">Tokens</div>
                    <div className="text-lg font-bold">{currentConv.total_tokens}</div>
                  </div>
                  <div className="bg-white p-3 rounded border">
                    <div className="text-xs text-gray-500">Cost</div>
                    <div className="text-lg font-bold">
                      ${currentConv.total_cost_usd.toFixed(4)}
                    </div>
                  </div>
                  <div className="bg-white p-3 rounded border">
                    <div className="text-xs text-gray-500">Status</div>
                    <div className="text-lg font-bold capitalize">{currentConv.status}</div>
                  </div>
                </div>

                {/* Advanced Metadata */}
                {currentConv.conv_metadata && (
                  <div className="mt-4 pt-4 border-t text-xs">
                    <div className="grid grid-cols-2 gap-2">
                      {currentConv.conv_metadata.ip_address && (
                        <div>📍 IP: {currentConv.conv_metadata.ip_address}</div>
                      )}
                      {currentConv.conv_metadata.country && (
                        <div>🌍 {currentConv.conv_metadata.country}</div>
                      )}
                      {currentConv.conv_metadata.city && (
                        <div>🏙️ {currentConv.conv_metadata.city}</div>
                      )}
                      {currentConv.conv_metadata.user_agent && (
                        <div className="col-span-2">🔧 {currentConv.conv_metadata.user_agent.substring(0, 50)}...</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                {loadingMessages ? (
                  <div className="text-center text-gray-500">Loading messages...</div>
                ) : selectedMessages.length === 0 ? (
                  <div className="text-center text-gray-500">No messages</div>
                ) : (
                  selectedMessages.map(msg => (
                    <div
                      key={msg.id}
                      className={`p-4 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-blue-100 ml-8'
                          : 'bg-white border border-gray-200 mr-8'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-bold text-sm">
                          {msg.role === 'user' ? '👤 You' : '🤖 AI'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(msg.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap mb-2">{msg.content}</p>
                      {msg.model_used && (
                        <div className="text-xs text-gray-600 space-x-3">
                          <span>Model: {msg.model_used}</span>
                          {msg.tokens_used && <span>• {msg.tokens_used} tokens</span>}
                          {msg.latency_ms && <span>• ⚡ {msg.latency_ms}ms</span>}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              Select a conversation to view details
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
