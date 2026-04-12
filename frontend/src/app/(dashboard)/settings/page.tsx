'use client'
import { useState } from 'react'

export default function SettingsPage() {
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4-turbo')
  const [temperature, setTemperature] = useState(0.7)

  const handleSave = async () => {
    try {
      const token = localStorage.getItem('access_token')
      await fetch('/api/v1/admin/ai-config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: 'Custom Config',
          provider,
          model_name: model,
          temperature,
          max_tokens: 2000,
          routing_strategy: 'balanced'
        })
      })
      alert('Settings saved!')
    } catch (e) {
      alert('Failed to save settings')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Settings</h1>
      
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-bold mb-4">AI Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Provider</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)} className="w-full px-3 py-2 border rounded">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="google">Google Gemini</option>
              <option value="ollama">Ollama</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full px-3 py-2 border rounded">
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="gemini-pro">Gemini Pro</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Temperature: {temperature}</label>
            <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full" />
          </div>
          <button onClick={handleSave} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Save Configuration
          </button>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">API Keys</h2>
        <button className="bg-green-600 text-white px-4 py-2 rounded">+ Create API Key</button>
      </div>
    </div>
  )
}
