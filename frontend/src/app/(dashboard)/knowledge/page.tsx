'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

interface KnowledgeSource {
  id: string
  name: string
  description: string
  type: string
  category: string
  status: string
  file_size: number
  chunk_count: number
  tags: string[]
  can_use_in_knowledge: boolean
  can_use_in_chat: boolean
  can_use_in_search: boolean
  is_active: boolean
  created_at: string
  client_id?: string
  source_name?: string
}

interface Conversation {
  id: string
  session_id: string
  title: string | null
  message_count: number
  created_at: string
}

export default function KnowledgePage() {
  const { token, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState('documents')
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [editingSource, setEditingSource] = useState<KnowledgeSource | null>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showArticleModal, setShowArticleModal] = useState(false)
  const [showConversionModal, setShowConversionModal] = useState(false)
  const [selectedConvId, setSelectedConvId] = useState<string>('')
  const [converting, setConverting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [articleForm, setArticleForm] = useState({
    name: '',
    description: '',
    content: '',
    tags: '',
    client_id: ''
  })

  const categories = ['documents', 'article', 'chat_session', 'client_document', 'training_material', 'reference']

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchSources()
      if (activeTab === 'chat_session') {
        fetchConversations()
      }
    }
  }, [activeTab, isAuthenticated, token])

  const fetchSources = async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/knowledge/sources?category=${activeTab}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSources(Array.isArray(data) ? data : (data.items || []))
      } else if (res.status === 401) {
        setError('Session expired. Please refresh the page.')
      }
    } catch (e) {
      console.error('Failed to fetch sources:', e)
      setError('Failed to load knowledge sources')
    } finally {
      setLoading(false)
    }
  }

  const fetchConversations = async () => {
    if (!token) return
    try {
      const res = await fetch('/api/v1/chat/conversations?page=1&page_size=100', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setConversations(data.items || [])
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !token) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('category', activeTab)

    try {
      const res = await fetch('/api/v1/knowledge/sources', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })
      if (res.ok) {
        setShowUploadModal(false)
        fetchSources()
      } else {
        setError('Upload failed')
      }
    } catch (e) {
      setError('Upload failed: ' + String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleArticleCreate = async () => {
    if (!token) return
    try {
      const res = await fetch('/api/v1/knowledge/articles', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: articleForm.name,
          description: articleForm.description,
          content: articleForm.content,
          tags: articleForm.tags.split(',').map(t => t.trim()),
          category: 'article',
          client_id: articleForm.client_id || null
        })
      })
      if (res.ok) {
        setShowArticleModal(false)
        setArticleForm({ name: '', description: '', content: '', tags: '', client_id: '' })
        fetchSources()
      } else {
        setError('Failed to create article')
      }
    } catch (e) {
      setError('Failed to create article: ' + String(e))
    }
  }

  const handleConvertConversation = async () => {
    if (!token || !selectedConvId) return

    setConverting(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/knowledge/sources/from-conversation/${selectedConvId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setShowConversionModal(false)
        setSelectedConvId('')
        fetchSources()
      } else if (res.status === 409) {
        setError('This conversation is already in the knowledge base')
      } else {
        setError('Failed to convert conversation')
      }
    } catch (e) {
      setError('Failed to convert conversation: ' + String(e))
    } finally {
      setConverting(false)
    }
  }

  const handleToggleUsage = async (sourceId: string, field: 'can_use_in_knowledge' | 'can_use_in_chat' | 'can_use_in_search') => {
    if (!token) return
    try {
      const source = sources.find(s => s.id === sourceId)
      if (!source) return

      const newValue = !source[field]
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ [field]: newValue })
      })
      if (res.ok) {
        fetchSources()
      }
    } catch (e) {
      setError('Failed to update source: ' + String(e))
    }
  }

  const handleDelete = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this knowledge source?') || !token) return

    try {
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        fetchSources()
      }
    } catch (e) {
      setError('Failed to delete source: ' + String(e))
    }
  }

  const handleApprove = async (sourceId: string) => {
    if (!token) return
    try {
      const res = await fetch(`/api/v1/knowledge/sources/${sourceId}/approve`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) fetchSources()
    } catch (e) {
      setError('Failed to approve: ' + String(e))
    }
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
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 p-4 text-sm text-red-700 rounded-lg">
          {error}
        </div>
      )}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Advanced Knowledge Management</h1>
        <div className="flex gap-2">
          <Link
            href="/knowledge/settings"
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
          >
            ⚙️ Settings
          </Link>
          {activeTab === 'article' ? (
            <button
              onClick={() => setShowArticleModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              + New Article
            </button>
          ) : activeTab === 'chat_session' ? (
            <button
              onClick={() => setShowConversionModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              + Add from Conversation
            </button>
          ) : (
            <button
              onClick={() => setShowUploadModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              + Upload
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b overflow-x-auto">
        {categories.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium border-b-2 whitespace-nowrap ${
              activeTab === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab.replace(/_/g, ' ').charAt(0).toUpperCase() + tab.replace(/_/g, ' ').slice(1)}
          </button>
        ))}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Upload {activeTab.replace(/_/g, ' ')}</h2>
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              className="block w-full mb-4"
              accept=".pdf,.docx,.txt,.csv,.json,.xlsx,.xls,.html"
            />
            {uploading && <p className="text-blue-600">Uploading...</p>}
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Article Modal */}
      {showArticleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Create New Article</h2>
            <input
              type="text"
              placeholder="Article Title"
              value={articleForm.name}
              onChange={(e) => setArticleForm({...articleForm, name: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3"
            />
            <textarea
              placeholder="Description"
              value={articleForm.description}
              onChange={(e) => setArticleForm({...articleForm, description: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 h-20"
            />
            <textarea
              placeholder="Article Content"
              value={articleForm.content}
              onChange={(e) => setArticleForm({...articleForm, content: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 h-40"
            />
            <input
              type="text"
              placeholder="Tags (comma separated)"
              value={articleForm.tags}
              onChange={(e) => setArticleForm({...articleForm, tags: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3"
            />
            <input
              type="text"
              placeholder="Client ID (optional)"
              value={articleForm.client_id}
              onChange={(e) => setArticleForm({...articleForm, client_id: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowArticleModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleArticleCreate}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Article
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conversation to Knowledge Modal */}
      {showConversionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Add Conversation to Knowledge Base</h2>
            <p className="text-sm text-gray-600 mb-4">Select a conversation to add it as a knowledge source:</p>
            <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
              {conversations.length === 0 ? (
                <p className="text-gray-500 text-sm">No conversations available</p>
              ) : (
                conversations.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => setSelectedConvId(conv.id)}
                    className={`w-full text-left p-3 rounded-lg border-2 transition ${
                      selectedConvId === conv.id
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium">{conv.title || 'Untitled'}</div>
                    <div className="text-xs text-gray-500">{conv.message_count} messages • {new Date(conv.created_at).toLocaleDateString()}</div>
                  </button>
                ))
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowConversionModal(false)
                  setSelectedConvId('')
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleConvertConversation}
                disabled={!selectedConvId || converting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {converting ? 'Converting...' : 'Add to Knowledge'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sources List */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Knowledge Sources</h2>
          {loading ? (
            <p className="text-gray-600">Loading...</p>
          ) : sources.length === 0 ? (
            <p className="text-gray-600">No sources in this category yet</p>
          ) : (
            <div className="space-y-4">
              {sources.map(source => (
                <div key={source.id} className="border rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{source.name}</h3>
                      <p className="text-sm text-gray-600">{source.description}</p>
                      <div className="flex gap-2 mt-2">
                        <span className={`text-xs px-2 py-1 rounded ${source.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {source.status}
                        </span>
                        <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                          {source.type}
                        </span>
                        {source.client_id && (
                          <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-800">
                            Client: {source.client_id}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-sm text-gray-600">
                      {source.file_size && <p>{(source.file_size / 1024).toFixed(1)} KB</p>}
                      <p>{source.chunk_count} chunks</p>
                    </div>
                  </div>

                  {/* Usage Controls */}
                  <div className="grid grid-cols-3 gap-3 mb-4 p-3 bg-gray-50 rounded">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={source.can_use_in_knowledge}
                        onChange={() => handleToggleUsage(source.id, 'can_use_in_knowledge')}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Use in Knowledge</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={source.can_use_in_chat}
                        onChange={() => handleToggleUsage(source.id, 'can_use_in_chat')}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Use in Chat</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={source.can_use_in_search}
                        onChange={() => handleToggleUsage(source.id, 'can_use_in_search')}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Use in Search</span>
                    </label>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    {source.status === 'pending' && (
                      <button
                        onClick={() => handleApprove(source.id)}
                        className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded hover:bg-green-200"
                      >
                        Approve
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(source.id)}
                      className="px-3 py-1 text-sm bg-red-100 text-red-800 rounded hover:bg-red-200"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
