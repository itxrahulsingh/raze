'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Globe, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { toast } from 'sonner'

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

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/knowledge/settings', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setSettings(data)
      }
    } catch {
      // keep defaults
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
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })
      if (res.ok) {
        setSaved(true)
        toast.success('Knowledge settings saved')
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e) {
      toast.error('Failed to save settings: ' + String(e))
    }
  }

  const toggleSetting = (key: keyof KnowledgeSettings) => {
    if (typeof settings[key] === 'boolean') {
      setSettings({
        ...settings,
        [key]: !settings[key],
      })
    }
  }

  const updateSetting = (key: keyof KnowledgeSettings, value: number) => {
    setSettings({
      ...settings,
      [key]: value,
    })
  }

  if (loading) {
    return (
      <div className="grid h-[70vh] place-items-center">
        <p className="text-sm text-muted-foreground">Loading knowledge settings...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Knowledge Policy</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Knowledge Settings Matrix</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Configure source categories, retrieval behavior, and governance rules for the knowledge engine.
            </p>
          </div>
          <Link href="/knowledge">
            <Button variant="outline">
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Back to Knowledge
            </Button>
          </Link>
        </div>
      </div>

      {saved && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          Settings saved successfully.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-primary" />
            Core Toggles
          </CardTitle>
          <CardDescription>Primary controls for enabling knowledge behavior.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {[
            ['enable_knowledge_base', 'Enable Knowledge Base'],
            ['knowledge_in_chat', 'Use in Chat Responses'],
            ['knowledge_in_search', 'Use in Search'],
            ['chat_session_knowledge_enabled', 'Enable Chat Session Knowledge'],
            ['enable_web_search', 'Enable Web Search'],
            ['require_source_approval', 'Require Source Approval'],
            ['auto_approve_sources', 'Auto-Approve Sources'],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center justify-between rounded-xl border border-border/70 p-3">
              <span className="text-sm">{label}</span>
              <Switch
                checked={settings[key as keyof KnowledgeSettings] as boolean}
                onCheckedChange={() => toggleSetting(key as keyof KnowledgeSettings)}
              />
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Allowed Source Types</CardTitle>
          <CardDescription>Control which source classes can be ingested.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['enable_documents', 'Documents'],
            ['enable_articles', 'Articles'],
            ['enable_client_documents', 'Client Documents'],
            ['enable_chat_sessions', 'Chat Sessions'],
            ['enable_training_materials', 'Training Materials'],
            ['enable_references', 'References'],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center justify-between rounded-xl border border-border/70 p-3">
              <span className="text-sm">{label}</span>
              <Switch
                checked={settings[key as keyof KnowledgeSettings] as boolean}
                onCheckedChange={() => toggleSetting(key as keyof KnowledgeSettings)}
              />
            </label>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Web Timeout</CardTitle>
            <CardDescription>Seconds for external retrieval calls.</CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              type="number"
              min="5"
              max="60"
              value={settings.web_search_timeout_seconds}
              onChange={(e) => updateSetting('web_search_timeout_seconds', parseInt(e.target.value || '0', 10))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Max Sources</CardTitle>
            <CardDescription>Upper bound for source inventory.</CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              type="number"
              min="10"
              max="10000"
              value={settings.max_knowledge_sources}
              onChange={(e) => updateSetting('max_knowledge_sources', parseInt(e.target.value || '0', 10))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Search Limit</CardTitle>
            <CardDescription>Sources returned per query.</CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              type="number"
              min="1"
              max="50"
              value={settings.knowledge_search_limit}
              onChange={(e) => updateSetting('knowledge_search_limit', parseInt(e.target.value || '0', 10))}
            />
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/30 bg-gradient-to-r from-primary/5 to-amber-100/40">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Globe className="h-4 w-4" />
            Web search: {settings.enable_web_search ? 'Enabled' : 'Disabled'}
            <Badge variant={settings.require_source_approval ? 'warning' : 'success'}>
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
              {settings.require_source_approval ? 'Manual approval' : 'Open approval'}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => fetchSettings()}>
              Reset
            </Button>
            <Button onClick={handleSave}>Save Settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
