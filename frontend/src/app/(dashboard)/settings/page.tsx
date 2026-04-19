'use client'

import { useEffect, useMemo, useState } from 'react'
import { Bot, KeyRound, Palette, RefreshCcw } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

type ProviderKey = 'openai' | 'anthropic' | 'gemini' | 'ollama' | 'grok'

interface ProviderConfig {
  apiKey?: string
  baseUrl?: string
  orgId?: string
}

interface AiConfigSummary {
  id: string
  name: string
  provider: ProviderKey
  model_name: string
  temperature: number
  max_tokens: number
  routing_strategy?: string
  is_default: boolean
}

const PROVIDER_MODELS: Record<ProviderKey, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4.1', 'gpt-4.1-mini'],
  anthropic: ['claude-3-5-sonnet', 'claude-3-opus', 'claude-3-haiku'],
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  ollama: [],
  grok: ['grok-2', 'grok-beta'],
}

const PROVIDER_KEYS: ProviderKey[] = ['openai', 'anthropic', 'gemini', 'ollama', 'grok']

function toProviderKey(value: string | undefined | null): ProviderKey {
  const normalized = (value || '').toLowerCase().trim()
  return PROVIDER_KEYS.includes(normalized as ProviderKey) ? (normalized as ProviderKey) : 'openai'
}

export default function SettingsPage() {
  const [mainTab, setMainTab] = useState('ai-config')
  const [providerSetupTab, setProviderSetupTab] = useState<ProviderKey>('openai')

  const [provider, setProvider] = useState<ProviderKey>('openai')
  const [model, setModel] = useState(PROVIDER_MODELS.openai[0])
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2000)
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant.')
  const [isDefault, setIsDefault] = useState(true)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [toolCalling, setToolCalling] = useState(true)
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [knowledgeEnabled, setKnowledgeEnabled] = useState(true)
  const [routingStrategy, setRoutingStrategy] = useState('balanced')

  const [providerConfigs, setProviderConfigs] = useState<Record<ProviderKey, ProviderConfig>>({
    openai: { apiKey: '', orgId: '' },
    anthropic: { apiKey: '' },
    gemini: { apiKey: '' },
    grok: { apiKey: '' },
    ollama: { baseUrl: 'http://localhost:11434' },
  })

  const [brandName, setBrandName] = useState('RAZE')
  const [brandColor, setBrandColor] = useState('#3B82F6')
  const [logoUrl, setLogoUrl] = useState('')

  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingOllamaModels, setLoadingOllamaModels] = useState(false)
  const [savedConfigs, setSavedConfigs] = useState<AiConfigSummary[]>([])
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [appSettings, setAppSettings] = useState<Record<string, any>>({})
  const [loadingAppSettings, setLoadingAppSettings] = useState(false)

  // Industry Config
  const [companyName, setCompanyName] = useState('')
  const [industryName, setIndustryName] = useState('')
  const [industryTopics, setIndustryTopics] = useState<string[]>([])
  const [topicInput, setTopicInput] = useState('')
  const [industryTone, setIndustryTone] = useState('friendly')
  const [restrictionMode, setRestrictionMode] = useState('strict')
  const [industrySystemPrompt, setIndustrySystemPrompt] = useState('')
  const [generatedPrompt, setGeneratedPrompt] = useState('')
  const [generatingPrompt, setGeneratingPrompt] = useState(false)

  const availableModels = useMemo(
    () => (provider === 'ollama' ? ollamaModels : PROVIDER_MODELS[provider]),
    [ollamaModels, provider]
  )

  useEffect(() => {
    fetchAiConfigs()
    fetchProviderConfigs()
    fetchWhiteLabelSettings()
    fetchAppSettings()
    fetchOllamaModels()
    fetchIndustryConfig()
  }, [])

  useEffect(() => {
    if (availableModels.length === 0) return
    if (!availableModels.includes(model)) {
      setModel(availableModels[0])
    }
  }, [availableModels, model])

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json',
  })

  const markSaved = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const fetchAiConfigs = async () => {
    try {
      const res = await fetch('/api/v1/admin/ai-configs', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) return
      const data = (await res.json()) as AiConfigSummary[]
      setSavedConfigs(data)

      const defaultConfig = data.find((item) => item.is_default) || data[0]
      if (!defaultConfig) return

      const nextProvider = toProviderKey(defaultConfig.provider)
      setProvider(nextProvider)
      setProviderSetupTab(nextProvider)
      setModel(defaultConfig.model_name)
      setTemperature(defaultConfig.temperature ?? 0.7)
      setMaxTokens(defaultConfig.max_tokens ?? 2000)
      setIsDefault(defaultConfig.is_default ?? true)
      setRoutingStrategy(defaultConfig.routing_strategy || 'balanced')
    } catch {
      // keep UI stable with defaults
    }
  }

  const fetchProviderConfigs = async () => {
    try {
      const res = await fetch('/api/v1/admin/provider-config', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) return
      const data = (await res.json()) as Record<ProviderKey, ProviderConfig>
      setProviderConfigs((prev) => ({ ...prev, ...data }))
    } catch {
      // keep defaults
    }
  }

  const fetchWhiteLabelSettings = async () => {
    try {
      const res = await fetch('/api/v1/admin/white-label', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) return
      const data = await res.json()
      setBrandName(data.brand_name || 'RAZE')
      setBrandColor(data.brand_color || '#3B82F6')
      setLogoUrl(data.logo_url || '')
    } catch {
      // keep UI stable with defaults
    }
  }

  const fetchAppSettings = async () => {
    try {
      setLoadingAppSettings(true)
      const res = await fetch('/api/v1/settings', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) return
      const data = await res.json()
      setAppSettings(data)
    } catch {
      // keep defaults
    } finally {
      setLoadingAppSettings(false)
    }
  }

  const handleSaveAppSettings = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify(appSettings),
      })
      if (!res.ok) throw new Error('Failed to save settings')
      const data = await res.json()
      setAppSettings(data)
      toast.success('App settings saved!')
      markSaved()
    } catch (err) {
      toast.error(`Failed to save: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleResetAppSettings = async () => {
    if (!window.confirm('Reset all app settings to defaults?')) return
    try {
      setLoading(true)
      const res = await fetch('/api/v1/settings/reset', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) throw new Error('Failed to reset settings')
      const data = await res.json()
      setAppSettings(data)
      toast.success('App settings reset to defaults!')
      markSaved()
    } catch (err) {
      toast.error(`Failed to reset: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const fetchOllamaModels = async () => {
    setLoadingOllamaModels(true)
    try {
      const res = await fetch('/api/v1/admin/ollama-models', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) {
        setOllamaModels([])
        return
      }
      const data = await res.json()
      setOllamaModels(data.models || [])
    } catch {
      setOllamaModels([])
    } finally {
      setLoadingOllamaModels(false)
    }
  }

  const fetchIndustryConfig = async () => {
    try {
      const res = await fetch('/api/v1/settings', {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) return
      const data = await res.json()
      setCompanyName(data.company_name || '')
      setIndustryName(data.industry_name || '')
      setIndustryTopics(Array.isArray(data.industry_topics) ? data.industry_topics :
                        typeof data.industry_topics === 'string' ? JSON.parse(data.industry_topics || '[]') : [])
      setIndustryTone(data.industry_tone || 'friendly')
      setRestrictionMode(data.industry_restriction_mode || 'strict')
      setIndustrySystemPrompt(data.industry_system_prompt || '')
    } catch {
      // keep defaults
    }
  }

  const handleGeneratePrompt = async () => {
    if (!industryName) {
      toast.error('Please enter an industry name')
      return
    }
    setGeneratingPrompt(true)
    try {
      const res = await fetch('/api/v1/settings/generate-prompt', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          industry_name: industryName,
          topics: industryTopics,
          tone: industryTone,
          restriction_mode: restrictionMode,
          company_name: companyName,
        }),
      })
      if (!res.ok) throw new Error('Failed to generate prompt')
      const data = await res.json()
      setGeneratedPrompt(data.prompt || '')
      setIndustrySystemPrompt(data.prompt || '')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate prompt')
    } finally {
      setGeneratingPrompt(false)
    }
  }

  const handleSaveIndustryConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({
          company_name: companyName,
          industry_name: industryName,
          industry_topics: industryTopics,
          industry_tone: industryTone,
          industry_restriction_mode: restrictionMode,
          industry_system_prompt: industrySystemPrompt,
        }),
      })
      if (!res.ok) throw new Error('Failed to save industry config')
      toast.success('Industry configuration saved!')
      markSaved()
      await fetchIndustryConfig()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save industry config')
    } finally {
      setLoading(false)
    }
  }

  const addTopic = () => {
    const topic = topicInput.trim()
    if (topic && !industryTopics.includes(topic)) {
      setIndustryTopics([...industryTopics, topic])
      setTopicInput('')
    }
  }

  const removeTopic = (topic: string) => {
    setIndustryTopics(industryTopics.filter(t => t !== topic))
  }

  const handleProviderChange = (nextProvider: ProviderKey) => {
    setProvider(nextProvider)
    const models = nextProvider === 'ollama' ? ollamaModels : PROVIDER_MODELS[nextProvider]
    if (models.length > 0 && !models.includes(model)) {
      setModel(models[0])
    }
  }

  const handleSaveAIConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/admin/ai-config', {
        method: 'POST',
        headers: authHeaders(),
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
          routing_strategy: routingStrategy,
        }),
      })
      if (!res.ok) throw new Error('Failed to save AI configuration')
      toast.success('AI configuration saved')
      markSaved()
      await fetchAiConfigs()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save AI configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveProviderConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/admin/provider-config', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(providerConfigs),
      })
      if (!res.ok) throw new Error('Failed to save provider configuration')
      toast.success('Provider credentials saved')
      markSaved()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save provider configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveWhiteLabel = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/admin/white-label', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          brand_name: brandName,
          brand_color: brandColor,
          logo_url: logoUrl,
        }),
      })
      if (!res.ok) throw new Error('Failed to save white label settings')
      toast.success('White-label settings saved')
      markSaved()
      await fetchWhiteLabelSettings()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save white label settings')
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

      {saved ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          Settings saved successfully.
        </div>
      ) : null}

      <Tabs value={mainTab} onValueChange={setMainTab}>
        <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0">
          <TabsTrigger value="ai-config">AI Configuration</TabsTrigger>
          <TabsTrigger value="providers">Provider Setup</TabsTrigger>
          <TabsTrigger value="white-label">White Label</TabsTrigger>
          <TabsTrigger value="industry-config">Industry Config</TabsTrigger>
          <TabsTrigger value="app-settings">App Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="ai-config">
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
                  {PROVIDER_KEYS.map((key) => (
                    <Button
                      key={key}
                      variant={provider === key ? 'default' : 'outline'}
                      onClick={() => handleProviderChange(key)}
                    >
                      {key.toUpperCase()}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-medium">Model</p>
                {provider === 'ollama' && loadingOllamaModels ? (
                  <p className="text-sm text-muted-foreground">Loading Ollama models...</p>
                ) : provider === 'ollama' && availableModels.length === 0 ? (
                  <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-700">
                    No Ollama models found.
                  </p>
                ) : (
                  <Select value={model} onChange={(event) => setModel(event.target.value)}>
                    {availableModels.map((entry) => (
                      <option key={entry} value={entry}>
                        {entry}
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
                  onChange={(event) => setSystemPrompt(event.target.value)}
                  placeholder="Custom system instructions for the AI..."
                />
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="mb-2 text-sm font-medium">Temperature: {temperature.toFixed(1)}</p>
                  <Input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(event) => setTemperature(parseFloat(event.target.value))}
                  />
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium">Max Tokens</p>
                  <Input
                    type="number"
                    min="100"
                    max="8192"
                    value={maxTokens}
                    onChange={(event) => setMaxTokens(parseInt(event.target.value || '0', 10))}
                  />
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium">Routing Strategy</p>
                  <Select value={routingStrategy} onChange={(event) => setRoutingStrategy(event.target.value)}>
                    <option value="balanced">Balanced</option>
                    <option value="performance">Performance</option>
                    <option value="cost">Cost</option>
                    <option value="latency">Latency</option>
                    <option value="round_robin">Round Robin</option>
                  </Select>
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
                    <Switch checked={value as boolean} onCheckedChange={(next) => (setter as (v: boolean) => void)(next)} />
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

              {savedConfigs.length > 0 ? (
                <div className="space-y-2 border-t border-border/70 pt-4">
                  <p className="text-sm font-medium">Saved Configurations</p>
                  <div className="flex flex-wrap gap-2">
                    {savedConfigs.slice(0, 8).map((entry) => (
                      <Badge key={entry.id} variant={entry.is_default ? 'success' : 'outline'}>
                        {entry.provider}:{entry.model_name}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="providers">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="h-5 w-5 text-primary" />
                Provider API Configuration
              </CardTitle>
              <CardDescription>Each provider tab is isolated to prevent config mixups.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Tabs value={providerSetupTab} onValueChange={(v) => setProviderSetupTab(toProviderKey(v))}>
                <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0">
                  {PROVIDER_KEYS.map((key) => (
                    <TabsTrigger key={key} value={key}>
                      {key.toUpperCase()}
                    </TabsTrigger>
                  ))}
                </TabsList>

                {PROVIDER_KEYS.map((key) => (
                  <TabsContent key={key} value={key} className="pt-4">
                    <div className="space-y-3 rounded-xl border border-border/70 p-4">
                      <p className="text-sm font-semibold">{key.toUpperCase()} Credentials</p>

                      {key === 'openai' ? (
                        <>
                          <Input
                            type="password"
                            placeholder="API Key (sk-...)"
                            value={providerConfigs.openai.apiKey || ''}
                            onChange={(event) =>
                              setProviderConfigs((prev) => ({
                                ...prev,
                                openai: { ...prev.openai, apiKey: event.target.value },
                              }))
                            }
                          />
                          <Input
                            placeholder="Organization ID (optional)"
                            value={providerConfigs.openai.orgId || ''}
                            onChange={(event) =>
                              setProviderConfigs((prev) => ({
                                ...prev,
                                openai: { ...prev.openai, orgId: event.target.value },
                              }))
                            }
                          />
                        </>
                      ) : null}

                      {key === 'anthropic' ? (
                        <Input
                          type="password"
                          placeholder="API Key"
                          value={providerConfigs.anthropic.apiKey || ''}
                          onChange={(event) =>
                            setProviderConfigs((prev) => ({
                              ...prev,
                              anthropic: { ...prev.anthropic, apiKey: event.target.value },
                            }))
                          }
                        />
                      ) : null}

                      {key === 'gemini' ? (
                        <Input
                          type="password"
                          placeholder="API Key"
                          value={providerConfigs.gemini.apiKey || ''}
                          onChange={(event) =>
                            setProviderConfigs((prev) => ({
                              ...prev,
                              gemini: { ...prev.gemini, apiKey: event.target.value },
                            }))
                          }
                        />
                      ) : null}

                      {key === 'grok' ? (
                        <Input
                          type="password"
                          placeholder="API Key"
                          value={providerConfigs.grok.apiKey || ''}
                          onChange={(event) =>
                            setProviderConfigs((prev) => ({
                              ...prev,
                              grok: { ...prev.grok, apiKey: event.target.value },
                            }))
                          }
                        />
                      ) : null}

                      {key === 'ollama' ? (
                        <>
                          <Input
                            placeholder="Base URL"
                            value={providerConfigs.ollama.baseUrl || ''}
                            onChange={(event) =>
                              setProviderConfigs((prev) => ({
                                ...prev,
                                ollama: { ...prev.ollama, baseUrl: event.target.value },
                              }))
                            }
                          />
                          <Button variant="outline" onClick={fetchOllamaModels} disabled={loadingOllamaModels}>
                            <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
                            {loadingOllamaModels ? 'Refreshing...' : 'Refresh Models'}
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </TabsContent>
                ))}
              </Tabs>

              <Button onClick={handleSaveProviderConfig} disabled={loading} className="w-full">
                {loading ? 'Saving...' : 'Save Provider Configuration'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="white-label">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5 text-primary" />
                White Label Branding
              </CardTitle>
              <CardDescription>Control dashboard and SDK brand identity.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input value={brandName} onChange={(event) => setBrandName(event.target.value)} placeholder="Brand Name" />
              <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
                <Input type="color" value={brandColor} onChange={(event) => setBrandColor(event.target.value)} className="h-11 p-1" />
                <Input value={brandColor} onChange={(event) => setBrandColor(event.target.value)} placeholder="#3B82F6" />
              </div>
              <Input value={logoUrl} onChange={(event) => setLogoUrl(event.target.value)} placeholder="Logo URL (https://...)" />

              <div className="rounded-xl border border-border/70 p-4">
                <p className="mb-2 text-sm font-medium">Live Preview</p>
                <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-card/50 p-3">
                  {logoUrl ? <img src={logoUrl} alt="logo" className="h-8 w-8 rounded" /> : null}
                  <span className="text-lg font-semibold" style={{ color: brandColor }}>
                    {brandName}
                  </span>
                </div>
              </div>

              <Button onClick={handleSaveWhiteLabel} disabled={loading} className="w-full">
                {loading ? 'Saving...' : 'Save White Label Settings'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="industry-config">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                Industry Configuration
              </CardTitle>
              <CardDescription>Configure industry-specific behavior, restrictions, and system prompts.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Company Name</label>
                  <Input
                    placeholder="e.g., Travel & Leisure Co"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Industry Name</label>
                  <Input
                    placeholder="e.g., Travel & Tourism"
                    value={industryName}
                    onChange={(e) => setIndustryName(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">Allowed Topics</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add topic (e.g., flights, hotels, destinations)"
                    value={topicInput}
                    onChange={(e) => setTopicInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addTopic()
                      }
                    }}
                  />
                  <Button onClick={addTopic}>Add</Button>
                </div>
                {industryTopics.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {industryTopics.map((topic) => (
                      <Badge key={topic} className="cursor-pointer" onClick={() => removeTopic(topic)}>
                        {topic} ✕
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Tone</label>
                  <Select value={industryTone} onChange={(e) => setIndustryTone(e.target.value)}>
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="casual">Casual</option>
                    <option value="formal">Formal</option>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">Restriction Mode</label>
                  <Select value={restrictionMode} onChange={(e) => setRestrictionMode(e.target.value)}>
                    <option value="strict">Strict (refuse off-topic)</option>
                    <option value="soft">Soft (prefer on-topic)</option>
                  </Select>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">System Prompt</label>
                <Textarea
                  rows={6}
                  value={industrySystemPrompt}
                  onChange={(e) => setIndustrySystemPrompt(e.target.value)}
                  placeholder="Leave empty to auto-generate from settings above..."
                />
              </div>

              <div className="flex gap-2">
                <Button onClick={handleGeneratePrompt} disabled={generatingPrompt || !industryName} variant="outline">
                  {generatingPrompt ? 'Generating...' : 'Generate System Prompt'}
                </Button>
                <Button onClick={handleSaveIndustryConfig} disabled={loading} className="flex-1">
                  {loading ? 'Saving...' : 'Save Industry Config'}
                </Button>
              </div>

              {generatedPrompt && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
                  <p className="mb-2 font-medium">Generated Prompt Preview:</p>
                  <p className="whitespace-pre-wrap text-xs">{generatedPrompt}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="app-settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5 text-primary" />
                Application Settings
              </CardTitle>
              <CardDescription>
                Manage branding, theme, chat configuration, and feature flags
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Brand Name</label>
                  <Input
                    placeholder="Application name"
                    value={appSettings.brand_name || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, brand_name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Brand Color</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={appSettings.brand_color || '#3B82F6'}
                      onChange={(e) => setAppSettings((prev) => ({ ...prev, brand_color: e.target.value }))}
                      className="h-10 w-10 rounded border border-input"
                    />
                    <Input
                      placeholder="#3B82F6"
                      value={appSettings.brand_color || ''}
                      onChange={(e) => setAppSettings((prev) => ({ ...prev, brand_color: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Logo URL</label>
                  <Input
                    placeholder="https://..."
                    value={appSettings.logo_url || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, logo_url: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Favicon URL</label>
                  <Input
                    placeholder="https://..."
                    value={appSettings.favicon_url || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, favicon_url: e.target.value }))}
                  />
                </div>

                <hr className="my-4" />

                <div>
                  <label className="text-sm font-medium">Page Title</label>
                  <Input
                    placeholder="Browser page title"
                    value={appSettings.page_title || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, page_title: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Page Description</label>
                  <Input
                    placeholder="Meta description"
                    value={appSettings.page_description || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, page_description: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Copyright Text</label>
                  <Input
                    placeholder="© 2026 Your Company"
                    value={appSettings.copyright_text || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, copyright_text: e.target.value }))}
                  />
                </div>

                <hr className="my-4" />

                <div>
                  <label className="text-sm font-medium">Chat Welcome Message</label>
                  <Textarea
                    placeholder="Initial greeting message"
                    value={appSettings.chat_welcome_message || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, chat_welcome_message: e.target.value }))}
                    rows={3}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Chat Input Placeholder</label>
                  <Input
                    placeholder="Input placeholder text"
                    value={appSettings.chat_placeholder || ''}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, chat_placeholder: e.target.value }))}
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Switch
                    checked={appSettings.enable_suggestions}
                    onCheckedChange={(checked) => setAppSettings((prev) => ({ ...prev, enable_suggestions: checked }))}
                  />
                  <label className="text-sm font-medium">Enable Chat Suggestions</label>
                </div>

                <hr className="my-4" />

                <div>
                  <label className="text-sm font-medium">Theme Mode</label>
                  <select
                    value={appSettings.theme_mode || 'dark'}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, theme_mode: e.target.value }))}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="dark">Dark</option>
                    <option value="light">Light</option>
                    <option value="auto">Auto</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Accent Color</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={appSettings.accent_color || '#3B82F6'}
                      onChange={(e) => setAppSettings((prev) => ({ ...prev, accent_color: e.target.value }))}
                      className="h-10 w-10 rounded border border-input"
                    />
                    <Input
                      placeholder="#3B82F6"
                      value={appSettings.accent_color || ''}
                      onChange={(e) => setAppSettings((prev) => ({ ...prev, accent_color: e.target.value }))}
                    />
                  </div>
                </div>

                <hr className="my-4" />

                <div className="space-y-2">
                  <label className="text-sm font-medium">Feature Flags</label>
                  {['enable_knowledge_base', 'enable_web_search', 'enable_memory', 'enable_voice'].map((flag) => (
                    <div key={flag} className="flex items-center gap-2">
                      <Switch
                        checked={appSettings[flag]}
                        onCheckedChange={(checked) => setAppSettings((prev) => ({ ...prev, [flag]: checked }))}
                      />
                      <label className="text-sm">{flag.replace('enable_', '').replace(/_/g, ' ').toUpperCase()}</label>
                    </div>
                  ))}
                </div>

                <div>
                  <label className="text-sm font-medium">Max File Size (MB)</label>
                  <Input
                    type="number"
                    min="1"
                    max="500"
                    value={appSettings.max_file_size_mb || 100}
                    onChange={(e) => setAppSettings((prev) => ({ ...prev, max_file_size_mb: parseInt(e.target.value) }))}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleSaveAppSettings} disabled={loading}>
                  {loading ? 'Saving...' : 'Save Settings'}
                </Button>
                <Button variant="outline" onClick={handleResetAppSettings} disabled={loading}>
                  Reset to Defaults
                </Button>
              </div>
              {saved && <p className="text-xs text-green-600">✓ Settings saved successfully</p>}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
