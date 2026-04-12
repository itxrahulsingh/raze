'use client'
import { useEffect, useState } from 'react'

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([])

  useEffect(() => {
    fetchConversations()
  }, [])

  const fetchConversations = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat/conversations', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setConversations(await res.json())
    } catch (e) {
      console.error('Failed to fetch conversations')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Conversations</h1>
      <div className="bg-white p-6 rounded-lg shadow">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b">
              <th className="pb-2">Title</th>
              <th className="pb-2">Messages</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {conversations.length > 0 ? (
              conversations.map((c: any) => (
                <tr key={c.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{c.title}</td>
                  <td>{c.message_count}</td>
                  <td><span className="bg-green-100 text-green-800 px-2 py-1 rounded">{c.status}</span></td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-4 text-center text-gray-600">No conversations</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
