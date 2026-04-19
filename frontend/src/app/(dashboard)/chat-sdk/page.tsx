'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Copy,
  Eye,
  EyeOff,
  Globe,
  KeyRound,
  Link2,
  Plus,
  RefreshCcw,
  ShieldCheck,
  SquareTerminal,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

interface ChatDomain {
  id: string
  domain: string
  display_name: string
  status: string
  is_active: boolean
  created_at: string
  last_used?: string
}

interface DomainSecretState {
  apiKey: string
  visible: boolean
}

interface RegisterResponse {
  domain_id: string
  domain: string
  api_key: string
  status: string
  message: string
}

function maskKey(apiKey: string) {
  if (apiKey.length <= 10) return '••••••••'
  return `${apiKey.slice(0, 10)}••••••••••••${apiKey.slice(-6)}`
}

export default function ChatSDKPage() {
  const [domains, setDomains] = useState<ChatDomain[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showNewDomain, setShowNewDomain] = useState(false)
  const [formData, setFormData] = useState({
    domain: '',
    display_name: '',
    description: '',
  })
  const [secretsByDomain, setSecretsByDomain] = useState<Record<string, DomainSecretState>>({})
  const [activeSecretDomainId, setActiveSecretDomainId] = useState<string | null>(null)

  const baseUrl = useMemo(() => {
    if (typeof window === 'undefined') return 'https://your-raze-url.com'
    return window.location.origin
  }, [])

  useEffect(() => {
    fetchDomains()
  }, [])

  const fetchDomains = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat-sdk/domains', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to fetch domains (${res.status})`)

      const data = await res.json()
      setDomains(data.domains || [])
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch domains'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const writeClipboard = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value)
      toast.success(`${label} copied`)
    } catch {
      toast.error(`Unable to copy ${label.toLowerCase()}`)
    }
  }

  const setSecret = (domainId: string, apiKey: string) => {
    setSecretsByDomain((prev) => ({
      ...prev,
      [domainId]: {
        apiKey,
        visible: false,
      },
    }))
    setActiveSecretDomainId(domainId)
  }

  const toggleKeyVisibility = (domainId: string) => {
    setSecretsByDomain((prev) => {
      const current = prev[domainId]
      if (!current) return prev
      const nextVisible = !current.visible
      if (nextVisible) {
        window.setTimeout(() => {
          setSecretsByDomain((latest) => {
            const latestSecret = latest[domainId]
            if (!latestSecret || !latestSecret.visible) return latest
            return {
              ...latest,
              [domainId]: { ...latestSecret, visible: false },
            }
          })
        }, 20000)
      }
      return {
        ...prev,
        [domainId]: {
          ...current,
          visible: nextVisible,
        },
      }
    })
  }

  const handleRegisterDomain = async () => {
    if (!formData.domain || !formData.display_name) {
      toast.error('Domain and display name are required')
      return
    }

    setSubmitting(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/chat-sdk/domains', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      const data = (await res.json()) as RegisterResponse | { detail?: string }
      if (!res.ok) {
        throw new Error((data as { detail?: string }).detail || 'Failed to register domain')
      }

      const created = data as RegisterResponse
      setSecret(created.domain_id, created.api_key)
      toast.success('Domain registered. API key generated.')
      setFormData({ domain: '', display_name: '', description: '' })
      setShowNewDomain(false)
      await fetchDomains()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to register domain'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const updateDomainStatus = async (domainId: string, action: 'approve' | 'suspend') => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}/${action}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to ${action} domain`)
      toast.success(`Domain ${action}d`)
      await fetchDomains()
    } catch (err) {
      const msg = err instanceof Error ? err.message : `Failed to ${action} domain`
      toast.error(msg)
    }
  }

  const regenerateApiKey = async (domain: ChatDomain) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domain.id}/regenerate-key`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = (await res.json()) as { api_key?: string; detail?: string }
      if (!res.ok || !data.api_key) {
        throw new Error(data.detail || 'Failed to regenerate API key')
      }
      setSecret(domain.id, data.api_key)
      toast.success('New API key generated')
      await fetchDomains()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to regenerate API key'
      toast.error(msg)
    }
  }

  const deleteDomain = async (domainId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to delete domain (${res.status})`)

      setDomains((prev) => prev.filter((item) => item.id !== domainId))
      setSecretsByDomain((prev) => {
        const next = { ...prev }
        delete next[domainId]
        return next
      })
      if (activeSecretDomainId === domainId) setActiveSecretDomainId(null)
      toast.success('Domain deleted')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete domain'
      toast.error(msg)
    }
  }

  const embedSnippet = (domain: ChatDomain, apiKey?: string) => {
    const keyValue = apiKey || 'PASTE_YOUR_API_KEY'
    return `<script>
  window.RAZE_CONFIG = {
    apiKey: '${keyValue}',
    apiUrl: '${baseUrl}/api/v1',
    position: 'bottom-right',
    theme: '#0F766E',
    domain: '${domain.domain}'
  };
</script>
<script src="${baseUrl}/raze-chat-widget.js"></script>`
  }

  const activeSecretDomain = activeSecretDomainId
    ? domains.find((domain) => domain.id === activeSecretDomainId) || null
    : null
  const activeSecret = activeSecretDomainId ? secretsByDomain[activeSecretDomainId] : undefined

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">SDK</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Enterprise Chat SDK Control</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Manage trusted domains, rotate API keys, and ship copy-ready embed snippets securely.
            </p>
          </div>
          <Button onClick={() => setShowNewDomain(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Register Domain
          </Button>
        </div>
      </div>

      <Card className="border-primary/30 bg-gradient-to-r from-primary/5 to-amber-100/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SquareTerminal className="h-5 w-5 text-primary" />
            Quick Integration
          </CardTitle>
          <CardDescription>Copy the script URL or full embed snippet in one click.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-xl border border-border/70 bg-card/60 p-3">
            <p className="text-xs text-muted-foreground">API base URL</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 break-all text-xs">{baseUrl}/api/v1</code>
              <Button size="sm" variant="outline" onClick={() => writeClipboard(`${baseUrl}/api/v1`, 'API base URL')}>
                <Copy className="mr-1.5 h-3.5 w-3.5" />
                Copy API URL
              </Button>
            </div>
          </div>
          <div className="rounded-xl border border-border/70 bg-card/60 p-3">
            <p className="text-xs text-muted-foreground">Widget script URL</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 break-all text-xs">{baseUrl}/raze-chat-widget.js</code>
              <Button
                size="sm"
                variant="outline"
                onClick={() => writeClipboard(`${baseUrl}/raze-chat-widget.js`, 'Script URL')}
              >
                <Link2 className="mr-1.5 h-3.5 w-3.5" />
                Copy URL
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registered Domains</CardTitle>
          <CardDescription>
            Domain boxes include approval, suspension, secure key rotation, embed copy, and delete.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading domains...</p>
          ) : domains.length === 0 ? (
            <p className="text-sm text-muted-foreground">No domains registered yet.</p>
          ) : (
            <div className="space-y-4">
              {domains.map((domain) => {
                const secret = secretsByDomain[domain.id]
                const keyText = secret ? (secret.visible ? secret.apiKey : maskKey(secret.apiKey)) : 'Hidden for security'
                return (
                  <div key={domain.id} className="rounded-2xl border border-border/70 bg-card/50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{domain.display_name}</p>
                        <p className="mt-1 flex items-center text-sm text-muted-foreground">
                          <Globe className="mr-1.5 h-3.5 w-3.5" />
                          {domain.domain}
                        </p>
                      </div>
                      <Badge
                        variant={
                          domain.status === 'approved'
                            ? 'success'
                            : domain.status === 'pending'
                            ? 'warning'
                            : 'outline'
                        }
                      >
                        {domain.status.toUpperCase()}
                      </Badge>
                    </div>

                    <div className="mt-3 rounded-xl border border-border/70 bg-background/60 p-3">
                      <p className="mb-1 text-xs text-muted-foreground">API Key</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="min-w-0 flex-1 break-all text-xs">{keyText}</code>
                        {secret ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleKeyVisibility(domain.id)}
                          >
                            {secret.visible ? <EyeOff className="mr-1.5 h-3.5 w-3.5" /> : <Eye className="mr-1.5 h-3.5 w-3.5" />}
                            {secret.visible ? 'Hide' : 'Reveal'}
                          </Button>
                        ) : null}
                        {secret ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => writeClipboard(secret.apiKey, 'API key')}
                          >
                            <Copy className="mr-1.5 h-3.5 w-3.5" />
                            Copy
                          </Button>
                        ) : null}
                        <Button variant="outline" size="sm" onClick={() => regenerateApiKey(domain)}>
                          <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
                          Regenerate
                        </Button>
                      </div>
                      {!secret ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Keys are shown only once. Use regenerate when you need to reveal a new key.
                        </p>
                      ) : secret.visible ? (
                        <p className="mt-2 text-xs text-muted-foreground">Auto-hide enabled after 20 seconds.</p>
                      ) : null}
                    </div>

                    <div className="mt-3 rounded-xl border border-border/70 bg-background/60 p-3">
                      <p className="mb-1 text-xs text-muted-foreground">Embed Snippet</p>
                      <pre className="max-h-28 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                        {embedSnippet(domain, secret?.apiKey)}
                      </pre>
                      <div className="mt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => writeClipboard(embedSnippet(domain, secret?.apiKey), 'Embed snippet')}
                        >
                          <Copy className="mr-1.5 h-3.5 w-3.5" />
                          Copy Embed Snippet
                        </Button>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span>
                        Last used: {domain.last_used ? new Date(domain.last_used).toLocaleString() : 'Never'}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {domain.status === 'pending' ? (
                          <Button variant="secondary" size="sm" onClick={() => updateDomainStatus(domain.id, 'approve')}>
                            <ShieldCheck className="mr-1.5 h-3.5 w-3.5" />
                            Approve
                          </Button>
                        ) : null}
                        {domain.status === 'approved' ? (
                          <Button variant="destructive" size="sm" onClick={() => updateDomainStatus(domain.id, 'suspend')}>
                            Suspend
                          </Button>
                        ) : null}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="outline" size="sm" className="border-destructive/30 text-destructive hover:bg-destructive/10">
                              <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                              Delete
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete this domain?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This permanently removes SDK access for <strong>{domain.domain}</strong>.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => deleteDomain(domain.id)}>
                                Delete Domain
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showNewDomain} onOpenChange={setShowNewDomain}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Register New Domain</DialogTitle>
            <DialogDescription>Create controlled SDK access for a website origin.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              placeholder="example.com"
              value={formData.domain}
              onChange={(event) => setFormData((prev) => ({ ...prev, domain: event.target.value }))}
            />
            <Input
              placeholder="Display name"
              value={formData.display_name}
              onChange={(event) => setFormData((prev) => ({ ...prev, display_name: event.target.value }))}
            />
            <Textarea
              placeholder="Description (optional)"
              rows={3}
              value={formData.description}
              onChange={(event) => setFormData((prev) => ({ ...prev, description: event.target.value }))}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewDomain(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleRegisterDomain} disabled={submitting}>
              {submitting ? 'Registering...' : 'Register'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(activeSecretDomain && activeSecret)} onOpenChange={() => setActiveSecretDomainId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              API Key Generated
            </DialogTitle>
            <DialogDescription>
              Save this key now. For security, we do not show full keys again unless regenerated.
            </DialogDescription>
          </DialogHeader>
          {activeSecretDomain && activeSecret ? (
            <div className="space-y-3">
              <div className="rounded-xl border border-border/70 bg-background/60 p-3">
                <p className="text-xs text-muted-foreground">Domain</p>
                <p className="text-sm font-medium">{activeSecretDomain.domain}</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/60 p-3">
                <p className="text-xs text-muted-foreground">API Key</p>
                <code className="mt-1 block break-all text-xs">{activeSecret.apiKey}</code>
                <div className="mt-2">
                  <Button size="sm" variant="outline" onClick={() => writeClipboard(activeSecret.apiKey, 'API key')}>
                    <Copy className="mr-1.5 h-3.5 w-3.5" />
                    Copy API Key
                  </Button>
                </div>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/60 p-3">
                <p className="text-xs text-muted-foreground">Embed Snippet</p>
                <pre className="max-h-36 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                  {embedSnippet(activeSecretDomain, activeSecret.apiKey)}
                </pre>
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => writeClipboard(embedSnippet(activeSecretDomain, activeSecret.apiKey), 'Embed snippet')}
                  >
                    <Copy className="mr-1.5 h-3.5 w-3.5" />
                    Copy Embed Snippet
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
          <DialogFooter>
            <Button onClick={() => setActiveSecretDomainId(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
