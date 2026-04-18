'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'

interface KnowledgeSettings {
  enable_knowledge_base: boolean
  enable_web_search: boolean
  enable_articles: boolean
  enable_documents: boolean
  enable_client_documents: boolean
  enable_chat_sessions: boolean
  enable_training_materials: boolean
  enable_references: boolean
  knowledge_in_chat: boolean
  knowledge_in_search: boolean
  max_knowledge_sources: number
  auto_approve_sources: boolean
  require_source_approval: boolean
  chat_session_knowledge_enabled: boolean
  web_search_timeout_seconds: number
  knowledge_search_limit: number
}

export default function KnowledgeSettingsPage() {
  const [settings, setSettings] = useState<KnowledgeSettings>({
    enable_knowledge_base: true,
    enable_web_search: true,
    enable_articles: true,
    enable_documents: true,
    enable_client_documents: true,
    enable_chat_sessions: true,
    enable_training_materials: true,
    enable_references: true,
    knowledge_in_chat: true,
    knowledge_in_search: true,
    max_knowledge_sources: 1000,
    auto_approve_sources: false,
    require_source_approval: true,
    chat_session_knowledge_enabled: true,
    web_search_timeout_seconds: 30,
    knowledge_search_limit: 10,
  })
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)
  const [chatPerms, setChatPerms] = useState<{[key: string]: boolean}>({})

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/knowledge/settings', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSettings(data)
      }
    } catch (e) {
      console.error('Failed to fetch settings:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/knowledge/settings', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e) {
      alert('Failed to save settings: ' + String(e))
    }
  }

  const toggleSetting = (key: keyof KnowledgeSettings) => {
    if (typeof settings[key] === 'boolean') {
      setSettings({
        ...settings,
        [key]: !settings[key]
      })
    }
  }

  const updateSetting = (key: keyof KnowledgeSettings, value: any) => {
    setSettings({
      ...settings,
      [key]: value
    })
  }

  if (loading) return <div className="p-6">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Knowledge Management Settings</h1>
          <p className="text-gray-600 mt-2">Configure knowledge features, permissions, and integrations</p>
        </div>
        <Link href="/knowledge" className="text-blue-600 hover:underline">
          ← Back to Knowledge
        </Link>
      </div>

      {saved && (
        <div className="bg-green-100 border border-green-400 text-green-800 px-4 py-3 rounded">
          Settings saved successfully!
        </div>
      )}

      {/* Master Toggle */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Master Controls</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enable_knowledge_base}
              onChange={() => toggleSetting('enable_knowledge_base')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Enable Knowledge Base</p>
              <p className="text-sm text-gray-600">Turn off to disable entire knowledge base system</p>
            </div>
          </label>
        </div>
      </div>

      {/* Knowledge Source Types */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Enabled Knowledge Source Types</h2>
        <p className="text-gray-600 mb-4">Control which types of knowledge can be stored and used</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { key: 'enable_documents', label: 'Documents', desc: 'PDF, DOCX, TXT, CSV files' },
            { key: 'enable_articles', label: 'Articles', desc: 'Text-based knowledge articles' },
            { key: 'enable_client_documents', label: 'Client Documents', desc: 'Client-specific files' },
            { key: 'enable_chat_sessions', label: 'Chat Sessions', desc: 'Conversation history' },
            { key: 'enable_training_materials', label: 'Training Materials', desc: 'Educational content' },
            { key: 'enable_references', label: 'References', desc: 'Reference materials' },
          ].map(({ key, label, desc }) => (
            <label key={key} className="flex items-start gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={settings[key as keyof KnowledgeSettings] as boolean}
                onChange={() => toggleSetting(key as keyof KnowledgeSettings)}
                className="w-5 h-5 mt-1"
              />
              <div className="flex-1">
                <p className="font-medium">{label}</p>
                <p className="text-sm text-gray-600">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Knowledge Usage Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Knowledge Usage Controls</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.knowledge_in_chat}
              onChange={() => toggleSetting('knowledge_in_chat')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Use in Chat Responses</p>
              <p className="text-sm text-gray-600">Allow knowledge base to be used in chat conversations</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.knowledge_in_search}
              onChange={() => toggleSetting('knowledge_in_search')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Use in Search</p>
              <p className="text-sm text-gray-600">Include knowledge in semantic and keyword searches</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.chat_session_knowledge_enabled}
              onChange={() => toggleSetting('chat_session_knowledge_enabled')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Enable Chat Session Knowledge</p>
              <p className="text-sm text-gray-600">Use past chat sessions as knowledge sources</p>
            </div>
          </label>
        </div>
      </div>

      {/* Web Search Integration */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Web Search Integration</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enable_web_search}
              onChange={() => toggleSetting('enable_web_search')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Enable Web Search</p>
              <p className="text-sm text-gray-600">Allow AI to search the web for answers when knowledge base insufficient</p>
            </div>
          </label>

          <div className="p-4 border rounded-lg">
            <label className="block mb-2">
              <p className="font-medium mb-2">Web Search Timeout (seconds)</p>
              <input
                type="number"
                min="5"
                max="60"
                value={settings.web_search_timeout_seconds}
                onChange={(e) => updateSetting('web_search_timeout_seconds', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </label>
          </div>
        </div>
      </div>

      {/* Source Management */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Source Management</h2>
        <div className="space-y-4">
          <div className="p-4 border rounded-lg">
            <label className="block mb-2">
              <p className="font-medium mb-2">Maximum Knowledge Sources</p>
              <input
                type="number"
                min="10"
                max="10000"
                value={settings.max_knowledge_sources}
                onChange={(e) => updateSetting('max_knowledge_sources', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <p className="text-sm text-gray-600 mt-1">Limit on total number of knowledge sources allowed</p>
            </label>
          </div>

          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.require_source_approval}
              onChange={() => toggleSetting('require_source_approval')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Require Source Approval</p>
              <p className="text-sm text-gray-600">Admin must approve new knowledge sources before use</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.auto_approve_sources}
              onChange={() => toggleSetting('auto_approve_sources')}
              className="w-5 h-5"
            />
            <div className="flex-1">
              <p className="font-bold">Auto-Approve Sources</p>
              <p className="text-sm text-gray-600">Automatically approve uploaded sources (requires admin upload)</p>
            </div>
          </label>

          <div className="p-4 border rounded-lg">
            <label className="block mb-2">
              <p className="font-medium mb-2">Default Knowledge Search Limit</p>
              <input
                type="number"
                min="1"
                max="50"
                value={settings.knowledge_search_limit}
                onChange={(e) => updateSetting('knowledge_search_limit', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <p className="text-sm text-gray-600 mt-1">Number of knowledge sources returned per search query</p>
            </label>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 font-medium"
        >
          Save Settings
        </button>
        <button
          onClick={() => fetchSettings()}
          className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
        >
          Reset
        </button>
      </div>
    </div>
  )
}
