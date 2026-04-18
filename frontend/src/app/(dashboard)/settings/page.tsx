'use client'

import { useEffect, useState } from 'react'
import { Bot, KeyRound, Palette, RefreshCcw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'

interface ProviderConfig {
  apiKey?: string
  baseUrl?: string
  orgId?: string
}

const PROVIDER_MODELS: { [key: string]: string[] } = {
  openai: ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'],
  anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
  gemini: ['gemini-pro', 'gemini-pro-vision'],
  ollama: [],
  grok: ['grok-2', 'grok-1'],
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('ai-config')
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4-turbo')
  const [availableModels, setAvailableModels] = useState<string[]>(PROVIDER_MODELS.openai)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2000)
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant.')
  const [isDefault, setIsDefault] = useState(true)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [toolCalling, setToolCalling] = useState(true)
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [knowledgeEnabled, setKnowledgeEnabled] = useState(true)

  const [providerConfigs, setProviderConfigs] = useState<{ [key: string]: ProviderConfig }>({
    openai: { apiKey: '', orgId: '' },
    anthropic: { apiKey: '' },
    gemini: { apiKey: '' },
    grok: { apiKey: '' },
    ollama: { baseUrl: 'http://localhost:11434' },
  })

  const [brandName, setBrandName] = useState('RAZE')
  const [brandColor, setBrandColor] = useState('#3B82F6')
  const [logoUrl, setLogoUrl] = useState('')

  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)

  useEffect(() => {
    fetchOllamaModels()
    fetchWhiteLabelSettings()
  }, [])

  const fetchWhiteLabelSettings = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/white-label', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setBrandName(data.brand_name || 'RAZE')
        setBrandColor(data.brand_color || '#3B82F6')
        setLogoUrl(data.logo_url || '')
      }
    } catch {
      // no-op
    }
  }

  const fetchOllamaModels = async () => {
    setLoadingModels(true)
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return
      const res = await fetch('/api/v1/admin/ollama-models', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        const models = data.models || []
        setAvailableModels(models)
        if (provider === 'ollama' && models.length > 0) {
          setModel(models[0])
        }
      }
    } catch {
      // no-op
    } finally {
      setLoadingModels(false)
    }
  }

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider)
    if (newProvider === 'ollama') {
      fetchOllamaModels()
    } else {
      const models = PROVIDER_MODELS[newProvider] || []
      setAvailableModels(models)
      if (models.length > 0) setModel(models[0])
    }
  }

  const handleSaveAIConfig = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/ai-config', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
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
        }),
      })
      if (res.ok) {
        setSaved(true)
        toast.success('AI configuration saved')
        setTimeout(() => setSaved(false), 3000)
      } else {
        toast.error('Failed to save configuration')
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
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
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(providerConfigs),
      })
      if (res.ok) {
        setSaved(true)
        toast.success('Provider configuration saved')
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
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
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: brandName,
          brand_color: brandColor,
          logo_url: logoUrl,
        }),
      })
      if (res.ok) {
        setSaved(true)
        toast.success('White label settings saved')
        setTimeout(() => setSaved(false), 3000)
        await fetchWhiteLabelSettings()
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Admin Settings</p>
        <h2 className="mt-2 text-3xl font-display font-semibold">Platform Configuration Studio</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Tune model behavior, provider credentials, and white-label identity from a unified control plane.
        </p>
      </div>

      {saved && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          Settings saved successfully.
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0">
          <TabsTrigger value="ai-config">AI Configuration</TabsTrigger>
          <TabsTrigger value="providers">Provider Setup</TabsTrigger>
          <TabsTrigger value="white-label">White Label</TabsTrigger>
        </TabsList>
      </Tabs>

      {activeTab === 'ai-config' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              AI Model Configuration
            </CardTitle>
            <CardDescription>Configure routing, runtime behavior, and generation defaults.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-medium">Provider</p>
              <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
                {Object.keys(PROVIDER_MODELS).map((p) => (
                  <Button
                    key={p}
                    variant={provider === p ? 'default' : 'outline'}
                    onClick={() => handleProviderChange(p)}
                  >
                    {p.toUpperCase()}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">Model</p>
              {provider === 'ollama' && loadingModels ? (
                <p className="text-sm text-muted-foreground">Loading Ollama models...</p>
              ) : availableModels.length === 0 && provider === 'ollama' ? (
                <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-700">
                  No Ollama models found.
                </p>
              ) : (
                <Select value={model} onChange={(e) => setModel(e.target.value)}>
                  {availableModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              )}
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">System Prompt</p>
              <Textarea
                rows={4}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Custom system instructions for the AI..."
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium">Temperature: {temperature.toFixed(1)}</p>
                <Input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium">Max Tokens</p>
                <Input
                  type="number"
                  min="100"
                  max="4096"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value || '0', 10))}
                />
              </div>
            </div>

            <div className="grid gap-3 rounded-xl border border-border/70 p-4 sm:grid-cols-2">
              {[
                ['Streaming Responses', streamingEnabled, setStreamingEnabled],
                ['Tool/Function Calling', toolCalling, setToolCalling],
                ['Memory Integration', memoryEnabled, setMemoryEnabled],
                ['Knowledge Integration', knowledgeEnabled, setKnowledgeEnabled],
              ].map(([label, value, setter], idx) => (
                <label key={idx} className="flex items-center justify-between rounded-lg border border-border/60 p-3 text-sm">
                  <span>{label as string}</span>
                  <Switch
                    checked={value as boolean}
                    onCheckedChange={(v) => (setter as (v: boolean) => void)(v)}
                  />
                </label>
              ))}
            </div>

            <label className="flex items-center justify-between rounded-lg border border-border/60 p-3 text-sm">
              <span>Set as default AI configuration</span>
              <Switch checked={isDefault} onCheckedChange={setIsDefault} />
            </label>

            <Button onClick={handleSaveAIConfig} disabled={loading} className="w-full">
              {loading ? 'Saving...' : 'Save AI Configuration'}
            </Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'providers' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              Provider API Configuration
            </CardTitle>
            <CardDescription>Store keys and endpoints for each inference provider.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {['openai', 'anthropic', 'gemini', 'grok', 'ollama'].map((providerName) => (
              <div key={providerName} className="rounded-xl border border-border/70 p-4">
                <p className="mb-2 text-sm font-semibold">{providerName.toUpperCase()}</p>
                {providerName === 'openai' && (
                  <div className="space-y-2">
                    <Input
                      type="password"
                      placeholder="API Key (sk-...)"
                      value={providerConfigs.openai?.apiKey || ''}
                      onChange={(e) =>
                        setProviderConfigs({
                          ...providerConfigs,
                          openai: { ...(providerConfigs.openai || {}), apiKey: e.target.value },
                        })
                      }
                    />
                    <Input
                      placeholder="Organization ID (optional)"
                      value={providerConfigs.openai?.orgId || ''}
                      onChange={(e) =>
                        setProviderConfigs({
                          ...providerConfigs,
                          openai: { ...(providerConfigs.openai || {}), orgId: e.target.value },
                        })
                      }
                    />
                  </div>
                )}
                {providerName === 'anthropic' && (
                  <Input
                    type="password"
                    placeholder="API Key"
                    value={providerConfigs.anthropic?.apiKey || ''}
                    onChange={(e) =>
                      setProviderConfigs({
                        ...providerConfigs,
                        anthropic: { ...(providerConfigs.anthropic || {}), apiKey: e.target.value },
                      })
                    }
                  />
                )}
                {providerName === 'gemini' && (
                  <Input
                    type="password"
                    placeholder="API Key"
                    value={providerConfigs.gemini?.apiKey || ''}
                    onChange={(e) =>
                      setProviderConfigs({
                        ...providerConfigs,
                        gemini: { ...(providerConfigs.gemini || {}), apiKey: e.target.value },
                      })
                    }
                  />
                )}
                {providerName === 'grok' && (
                  <Input
                    type="password"
                    placeholder="API Key"
                    value={providerConfigs.grok?.apiKey || ''}
                    onChange={(e) =>
                      setProviderConfigs({
                        ...providerConfigs,
                        grok: { ...(providerConfigs.grok || {}), apiKey: e.target.value },
                      })
                    }
                  />
                )}
                {providerName === 'ollama' && (
                  <Input
                    placeholder="Base URL"
                    value={providerConfigs.ollama?.baseUrl || ''}
                    onChange={(e) =>
                      setProviderConfigs({
                        ...providerConfigs,
                        ollama: { ...(providerConfigs.ollama || {}), baseUrl: e.target.value },
                      })
                    }
                  />
                )}
              </div>
            ))}

            <Button onClick={handleSaveProviderConfig} disabled={loading} className="w-full">
              {loading ? 'Saving...' : 'Save Provider Configuration'}
            </Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'white-label' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5 text-primary" />
              White Label Settings
            </CardTitle>
            <CardDescription>Customize brand identity for admin and end-user experiences.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="mb-2 text-sm font-medium">Brand Name</p>
              <Input value={brandName} onChange={(e) => setBrandName(e.target.value)} placeholder="e.g., Acme AI" />
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">Primary Brand Color</p>
              <div className="flex gap-3">
                <Input type="color" value={brandColor} onChange={(e) => setBrandColor(e.target.value)} className="w-20 p-1" />
                <Input value={brandColor} onChange={(e) => setBrandColor(e.target.value)} className="font-mono" />
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium">Logo URL</p>
              <Input value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} placeholder="https://example.com/logo.png" />
            </div>

            <div className="rounded-xl border border-border/70 bg-secondary/30 p-4">
              <p className="mb-2 text-sm font-medium">Preview</p>
              <div className="rounded-lg border-b-4 bg-background p-4" style={{ borderColor: brandColor }}>
                <p className="text-xl font-semibold" style={{ color: brandColor }}>{brandName}</p>
                <p className="text-sm text-muted-foreground">Your branded AI assistant</p>
              </div>
              <Badge variant="outline" className="mt-3">
                <RefreshCcw className="mr-1 h-3.5 w-3.5" />
                Updates apply after refresh
              </Badge>
            </div>

            <Button onClick={handleSaveWhiteLabel} disabled={loading} className="w-full">
              {loading ? 'Saving...' : 'Save White Label Settings'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
