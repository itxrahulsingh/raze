'use client'
import { useEffect, useState } from 'react'

interface ChatDomain {
  id: string
  domain: string
  display_name: string
  status: string
  is_active: boolean
  api_key?: string
  created_at: string
  last_used?: string
}

export default function ChatSDKPage() {
  const [domains, setDomains] = useState<ChatDomain[]>([])
  const [loading, setLoading] = useState(true)
  const [showNewDomain, setShowNewDomain] = useState(false)
  const [formData, setFormData] = useState({
    domain: '',
    display_name: '',
    description: '',
  })
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  useEffect(() => {
    fetchDomains()
  }, [])

  const fetchDomains = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat-sdk/domains', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setDomains(data.domains || [])
      }
    } catch (e) {
      console.error('Failed to fetch domains:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleRegisterDomain = async () => {
    if (!formData.domain || !formData.display_name) {
      alert('Domain and display name are required')
      return
    }

    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat-sdk/domains', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })

      if (res.ok) {
        const data = await res.json()
        // Show API key once
        alert(`✅ Domain registered!\n\nAPI Key: ${data.api_key}\n\nSave this - it won't be shown again!`)
        setFormData({ domain: '', display_name: '', description: '' })
        setShowNewDomain(false)
        fetchDomains()
      } else {
        const error = await res.json()
        alert('Error: ' + error.detail)
      }
    } catch (e) {
      alert('Error: ' + String(e))
    }
  }

  const handleApproveDomain = async (domainId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}/approve`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        fetchDomains()
      }
    } catch (e) {
      alert('Error: ' + String(e))
    }
  }

  const handleSuspendDomain = async (domainId: string) => {
    if (!confirm('Suspend this domain?')) return
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}/suspend`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        fetchDomains()
      }
    } catch (e) {
      alert('Error: ' + String(e))
    }
  }

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Chat SDK Management</h1>
        <button
          onClick={() => setShowNewDomain(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          + Register Domain
        </button>
      </div>

      {/* Integration Guide */}
      <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg">
        <h2 className="font-bold text-blue-900 mb-3">🚀 How to Use Chat SDK</h2>
        <div className="text-sm text-blue-800 space-y-2">
          <p><strong>1. Register your domain</strong> - Register the website where you'll embed the chat</p>
          <p><strong>2. Get your API key</strong> - Save it (shown only once!)</p>
          <p><strong>3. Add to your website</strong> - Insert this code before closing &lt;/body&gt; tag:</p>
          <pre className="bg-white p-3 rounded border border-blue-200 mt-2 overflow-x-auto text-xs">
{`<script>
  window.RAZE_CONFIG = {
    apiKey: 'your-api-key-here',
    apiUrl: 'https://your-raze-url.com',
    position: 'bottom-right',
    theme: '#3B82F6'
  };
</script>
<script src="https://your-raze-url.com/raze-chat-widget.js"></script>`}
          </pre>
        </div>
      </div>

      {/* Register Domain Modal */}
      {showNewDomain && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Register New Domain</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Domain *</label>
                <input
                  type="text"
                  placeholder="example.com"
                  value={formData.domain}
                  onChange={(e) => setFormData({...formData, domain: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Display Name *</label>
                <input
                  type="text"
                  placeholder="My Website"
                  value={formData.display_name}
                  onChange={(e) => setFormData({...formData, display_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  placeholder="Optional description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowNewDomain(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRegisterDomain}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Register
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Domains List */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Registered Domains</h2>

          {loading ? (
            <p className="text-gray-600">Loading...</p>
          ) : domains.length === 0 ? (
            <p className="text-gray-600">No domains registered yet</p>
          ) : (
            <div className="space-y-4">
              {domains.map(domain => (
                <div key={domain.id} className="border rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-bold text-lg">{domain.display_name}</h3>
                      <p className="text-sm text-gray-600">{domain.domain}</p>
                    </div>
                    <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                      domain.status === 'approved'
                        ? 'bg-green-100 text-green-800'
                        : domain.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {domain.status.toUpperCase()}
                    </span>
                  </div>

                  {domain.api_key && (
                    <div className="mb-3 p-3 bg-gray-50 rounded border border-gray-200">
                      <p className="text-xs text-gray-600 mb-1">API Key</p>
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-mono flex-1 break-all">{domain.api_key}</code>
                        <button
                          onClick={() => copyToClipboard(domain.api_key!, domain.id)}
                          className="text-sm bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded"
                        >
                          {copiedKey === domain.id ? '✓ Copied' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="text-sm text-gray-600 mb-3">
                    {domain.last_used ? (
                      <p>Last used: {new Date(domain.last_used).toLocaleString()}</p>
                    ) : (
                      <p>Not yet used</p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    {domain.status === 'pending' && (
                      <button
                        onClick={() => handleApproveDomain(domain.id)}
                        className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded hover:bg-green-200"
                      >
                        ✓ Approve
                      </button>
                    )}
                    {domain.status === 'approved' && (
                      <button
                        onClick={() => handleSuspendDomain(domain.id)}
                        className="px-3 py-1 text-sm bg-red-100 text-red-800 rounded hover:bg-red-200"
                      >
                        Suspend
                      </button>
                    )}
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
