'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'

interface ConversationStats {
  total_conversations: number
  active_conversations: number
  total_messages: number
  total_tokens: number
  total_cost_usd: number
  avg_tokens_per_conversation: number
  avg_cost_per_conversation: number
}

interface SessionStats {
  total_sessions: number
  active_sessions: number
  total_session_messages: number
}

interface ConversationItem {
  id: string
  title: string | null
  message_count: number
  total_tokens: number
  created_at: string
  status: string
}

export default function AdminDashboard() {
  const [convStats, setConvStats] = useState<ConversationStats | null>(null)
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null)
  const [recentConversations, setRecentConversations] = useState<ConversationItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const headers = { 'Authorization': `Bearer ${token}` }

      // Fetch conversation stats
      const statsRes = await fetch('/api/v1/admin/stats', { headers })
      if (statsRes.ok) {
        const data = await statsRes.json()
        setConvStats(data)
      }

      // Fetch session stats
      const sessionsRes = await fetch('/api/v1/admin/session-stats', { headers })
      if (sessionsRes.ok) {
        const data = await sessionsRes.json()
        setSessionStats(data)
      }

      // Fetch recent conversations
      const convRes = await fetch('/api/v1/chat/conversations?page=1&page_size=10', { headers })
      if (convRes.ok) {
        const data = await convRes.json()
        setRecentConversations(data.items || [])
      }
    } catch (e) {
      console.error('Failed to fetch dashboard data:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-600 mt-2">System overview and management</p>
        </div>
        <div className="flex gap-3">
          <Link href="/admin-chat">
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              💬 New Chat
            </button>
          </Link>
          <Link href="/conversations">
            <button className="px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300">
              📋 Conversations
            </button>
          </Link>
        </div>
      </div>

      {/* Overview Cards */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading dashboard...</div>
      ) : (
        <>
          {/* Conversation Stats */}
          {convStats && (
            <div>
              <h2 className="text-xl font-bold mb-4">Conversation Statistics</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Total Conversations</p>
                  <p className="text-3xl font-bold mt-1">{convStats.total_conversations}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Active</p>
                  <p className="text-3xl font-bold text-green-600 mt-1">{convStats.active_conversations}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Total Messages</p>
                  <p className="text-3xl font-bold mt-1">{convStats.total_messages}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Total Tokens</p>
                  <p className="text-3xl font-bold mt-1">{convStats.total_tokens.toLocaleString()}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Total Cost</p>
                  <p className="text-3xl font-bold text-blue-600 mt-1">${convStats.total_cost_usd.toFixed(2)}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Avg Cost/Conv</p>
                  <p className="text-3xl font-bold mt-1">${convStats.avg_cost_per_conversation.toFixed(4)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Session Stats */}
          {sessionStats && (
            <div>
              <h2 className="text-xl font-bold mb-4">Session Statistics</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Total Sessions</p>
                  <p className="text-3xl font-bold mt-1">{sessionStats.total_sessions}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Active Sessions</p>
                  <p className="text-3xl font-bold text-green-600 mt-1">{sessionStats.active_sessions}</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <p className="text-sm text-gray-600">Session Messages</p>
                  <p className="text-3xl font-bold mt-1">{sessionStats.total_session_messages}</p>
                </div>
              </div>
            </div>
          )}

          {/* Recent Conversations */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Recent Conversations</h2>
              <Link href="/conversations" className="text-blue-600 hover:underline text-sm">
                View all →
              </Link>
            </div>
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Title</th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Messages</th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Tokens</th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Created</th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {recentConversations.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                        No conversations yet
                      </td>
                    </tr>
                  ) : (
                    recentConversations.map(conv => (
                      <tr key={conv.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm font-medium text-gray-900 max-w-xs truncate">
                          {conv.title || 'Untitled'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{conv.message_count}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{conv.total_tokens.toLocaleString()}</td>
                        <td className="px-6 py-4 text-sm">
                          <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                            {conv.status || 'active'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {new Date(conv.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <Link
                            href={`/conversations?id=${conv.id}`}
                            className="text-blue-600 hover:underline"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h2 className="text-xl font-bold mb-4">Management Tools</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Link href="/admin-chat">
                <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg cursor-pointer transition">
                  <div className="text-3xl mb-2">💬</div>
                  <h3 className="font-bold">Chat Interface</h3>
                  <p className="text-sm text-gray-600 mt-1">Test AI responses with streaming</p>
                </div>
              </Link>
              <Link href="/conversations">
                <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg cursor-pointer transition">
                  <div className="text-3xl mb-2">📋</div>
                  <h3 className="font-bold">Conversations</h3>
                  <p className="text-sm text-gray-600 mt-1">Manage chat history and data</p>
                </div>
              </Link>
              <Link href="/analytics">
                <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg cursor-pointer transition">
                  <div className="text-3xl mb-2">📊</div>
                  <h3 className="font-bold">Analytics</h3>
                  <p className="text-sm text-gray-600 mt-1">Usage metrics and insights</p>
                </div>
              </Link>
              <Link href="/settings">
                <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg cursor-pointer transition">
                  <div className="text-3xl mb-2">⚙️</div>
                  <h3 className="font-bold">Settings</h3>
                  <p className="text-sm text-gray-600 mt-1">Configure AI and providers</p>
                </div>
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
