'use client'
import { useEffect, useState } from 'react'

interface AIConfig {
  name: string
  provider: string
  model_name: string
  temperature: number
  max_tokens: number
  system_prompt: string
  is_default: boolean
  is_active: boolean
  streaming_enabled: boolean
  tool_calling_enabled: boolean
  memory_enabled: boolean
  knowledge_enabled: boolean
  fallback_provider?: string
  fallback_model?: string
}

interface ProviderConfig {
  apiKey?: string
  baseUrl?: string
  orgId?: string
}

const PROVIDER_MODELS: {[key: string]: string[]} = {
  openai: ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'],
  anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
  gemini: ['gemini-pro', 'gemini-pro-vision'],
  ollama: [], // Will be populated dynamically
  grok: ['grok-2', 'grok-1'],
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('ai-config')
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4-turbo')
  const [availableModels, setAvailableModels] = useState<string[]>(PROVIDER_MODELS['openai'])
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2000)
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant.')
  const [isDefault, setIsDefault] = useState(true)

  // Feature toggles
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [toolCalling, setToolCalling] = useState(true)
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [knowledgeEnabled, setKnowledgeEnabled] = useState(true)

  // Provider configs
  const [providerConfigs, setProviderConfigs] = useState<{[key: string]: ProviderConfig}>({
    openai: { apiKey: '', orgId: '' },
    anthropic: { apiKey: '' },
    gemini: { apiKey: '' },
    grok: { apiKey: '' },
    ollama: { baseUrl: 'http://localhost:11434' },
  })

  // White label settings
  const [brandName, setBrandName] = useState('RAZE')
  const [brandColor, setBrandColor] = useState('#3B82F6')
  const [logoUrl, setLogoUrl] = useState('')

  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetchOllamaModels()
  }, [])

  const fetchOllamaModels = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/ollama-models', {
        headers: {
          'Authorization': `Bearer ${token}`,
        }
      })
      if (res.ok) {
        const data = await res.json()
        setAvailableModels(data.models || [])
      }
    } catch (e) {
      console.error('Failed to fetch Ollama models:', e)
    }
  }

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider)
    const models = PROVIDER_MODELS[newProvider] || []
    setAvailableModels(models)
    if (models.length > 0) {
      setModel(models[0])
    }
  }

  const handleSaveAIConfig = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/ai-config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: `${provider} - ${model}`,
          provider,
          model_name: model,
          temperature,
          max_tokens: maxTokens,
          system_prompt: systemPrompt,
          is_default: isDefault,
          is_active: true,
          streaming_enabled: streamingEnabled,
          tool_calling_enabled: toolCalling,
          memory_enabled: memoryEnabled,
          knowledge_enabled: knowledgeEnabled,
        })
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      } else {
        alert('Failed to save configuration')
      }
    } catch (e) {
      alert('Error: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  const handleSaveProviderConfig = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/provider-config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(providerConfigs)
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e) {
      alert('Error: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  const handleSaveWhiteLabel = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/white-label', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          brand_name: brandName,
          brand_color: brandColor,
          logo_url: logoUrl,
        })
      })
      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e) {
      alert('Error: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Admin Settings</h1>

      {saved && (
        <div className="bg-green-100 border border-green-400 text-green-800 px-4 py-3 rounded">
          Settings saved successfully!
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {[
          { id: 'ai-config', label: 'AI Configuration' },
          { id: 'providers', label: 'Provider Setup' },
          { id: 'white-label', label: 'White Label' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 font-medium border-b-2 ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* AI Configuration Tab */}
      {activeTab === 'ai-config' && (
        <div className="bg-white p-6 rounded-lg shadow space-y-6">
          <h2 className="text-xl font-bold">AI Model Configuration</h2>

          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-bold mb-2">Provider *</label>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {Object.keys(PROVIDER_MODELS).map(p => (
                <button
                  key={p}
                  onClick={() => handleProviderChange(p)}
                  className={`p-3 rounded border-2 font-medium text-center ${
                    provider === p
                      ? 'border-blue-600 bg-blue-50 text-blue-600'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-bold mb-2">Model *</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              {availableModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            {provider === 'ollama' && availableModels.length === 0 && (
              <p className="text-yellow-600 text-sm mt-2">No Ollama models found. Make sure Ollama is running.</p>
            )}
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-bold mb-2">System Prompt</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="Custom system instructions for the AI..."
            />
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-bold mb-2">Temperature: {temperature.toFixed(1)}</label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-gray-600 mt-1">0 = deterministic, 2 = creative</p>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-bold mb-2">Max Tokens</label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="100"
              max="4096"
            />
          </div>

          {/* Feature Toggles */}
          <div className="border-t pt-4">
            <h3 className="font-bold mb-3">Feature Toggles</h3>
            <div className="space-y-3">
              {[
                { key: 'streamingEnabled', label: 'Streaming Responses', value: streamingEnabled, setter: setStreamingEnabled },
                { key: 'toolCalling', label: 'Tool/Function Calling', value: toolCalling, setter: setToolCalling },
                { key: 'memoryEnabled', label: 'Memory (Conversation History)', value: memoryEnabled, setter: setMemoryEnabled },
                { key: 'knowledgeEnabled', label: 'Knowledge Base Integration', value: knowledgeEnabled, setter: setKnowledgeEnabled },
              ].map(({key, label, value, setter}) => (
                <label key={key} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => setter(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Default Config */}
          <label className="flex items-center gap-3 cursor-pointer p-3 border rounded-lg">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="w-4 h-4"
            />
            <span>Set as default AI configuration</span>
          </label>

          <button
            onClick={handleSaveAIConfig}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Saving...' : 'Save AI Configuration'}
          </button>
        </div>
      )}

      {/* Provider Setup Tab */}
      {activeTab === 'providers' && (
        <div className="bg-white p-6 rounded-lg shadow space-y-6">
          <h2 className="text-xl font-bold">Provider API Configuration</h2>

          {/* OpenAI */}
          <div className="border-l-4 border-blue-500 p-4 bg-blue-50 rounded">
            <h3 className="font-bold mb-3">OpenAI</h3>
            <input
              type="password"
              placeholder="API Key (sk-...)"
              value={providerConfigs.openai?.apiKey || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                openai: {...(providerConfigs.openai || {}), apiKey: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-2"
            />
            <input
              type="text"
              placeholder="Organization ID (optional)"
              value={providerConfigs.openai?.orgId || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                openai: {...(providerConfigs.openai || {}), orgId: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Anthropic */}
          <div className="border-l-4 border-red-500 p-4 bg-red-50 rounded">
            <h3 className="font-bold mb-3">Anthropic (Claude)</h3>
            <input
              type="password"
              placeholder="API Key"
              value={providerConfigs.anthropic?.apiKey || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                anthropic: {...(providerConfigs.anthropic || {}), apiKey: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Gemini */}
          <div className="border-l-4 border-yellow-500 p-4 bg-yellow-50 rounded">
            <h3 className="font-bold mb-3">Google Gemini</h3>
            <input
              type="password"
              placeholder="API Key"
              value={providerConfigs.gemini?.apiKey || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                gemini: {...(providerConfigs.gemini || {}), apiKey: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Grok */}
          <div className="border-l-4 border-purple-500 p-4 bg-purple-50 rounded">
            <h3 className="font-bold mb-3">Grok (xAI)</h3>
            <input
              type="password"
              placeholder="API Key"
              value={providerConfigs.grok?.apiKey || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                grok: {...(providerConfigs.grok || {}), apiKey: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Ollama */}
          <div className="border-l-4 border-green-500 p-4 bg-green-50 rounded">
            <h3 className="font-bold mb-3">Ollama (Local)</h3>
            <input
              type="text"
              placeholder="Base URL (default: http://localhost:11434)"
              value={providerConfigs.ollama?.baseUrl || ''}
              onChange={(e) => setProviderConfigs({
                ...providerConfigs,
                ollama: {...(providerConfigs.ollama || {}), baseUrl: e.target.value}
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="text-sm text-gray-600 mt-2">
              Install Ollama: <a href="https://ollama.ai" target="_blank" className="text-blue-600 underline">ollama.ai</a>
            </p>
          </div>

          <button
            onClick={handleSaveProviderConfig}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Saving...' : 'Save Provider Configuration'}
          </button>
        </div>
      )}

      {/* White Label Tab */}
      {activeTab === 'white-label' && (
        <div className="bg-white p-6 rounded-lg shadow space-y-6">
          <h2 className="text-xl font-bold">White Label Settings</h2>

          <div>
            <label className="block text-sm font-bold mb-2">Brand Name</label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="e.g., MyAI, Acme Corp AI"
            />
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">Primary Brand Color</label>
            <div className="flex gap-4">
              <input
                type="color"
                value={brandColor}
                onChange={(e) => setBrandColor(e.target.value)}
                className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
              />
              <input
                type="text"
                value={brandColor}
                onChange={(e) => setBrandColor(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg font-mono"
                placeholder="#3B82F6"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">Logo URL</label>
            <input
              type="text"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="https://example.com/logo.png"
            />
            {logoUrl && <img src={logoUrl} alt="Logo preview" className="mt-4 max-w-xs h-auto" />}
          </div>

          <div className="p-4 bg-gray-50 rounded border border-gray-300">
            <h3 className="font-bold mb-2">Preview</h3>
            <div style={{borderColor: brandColor}} className="border-b-4 p-4 bg-white rounded">
              <h1 style={{color: brandColor}} className="text-2xl font-bold">{brandName}</h1>
              <p className="text-gray-600">Your branded AI assistant</p>
            </div>
          </div>

          <button
            onClick={handleSaveWhiteLabel}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Saving...' : 'Save White Label Settings'}
          </button>
        </div>
      )}
    </div>
  )
}
