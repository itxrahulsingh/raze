'use client'
import { useEffect, useState } from 'react'
import { Copy, Globe, Plus, ShieldCheck, SquareTerminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { toast } from 'sonner'

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
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setDomains(data.domains || [])
      }
    } catch {
      // no-op
    } finally {
      setLoading(false)
    }
  }

  const handleRegisterDomain = async () => {
    if (!formData.domain || !formData.display_name) {
      toast.error('Domain and display name are required')
      return
    }

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

      if (res.ok) {
        const data = await res.json()
        toast.success('Domain registered successfully')
        if (data.api_key) {
          toast.info('API key issued. Copy and store it securely.')
        }
        setFormData({ domain: '', display_name: '', description: '' })
        setShowNewDomain(false)
        fetchDomains()
      } else {
        const error = await res.json()
        toast.error(error.detail || 'Failed to register domain')
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
    }
  }

  const handleApproveDomain = async (domainId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}/approve`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        toast.success('Domain approved')
        fetchDomains()
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
    }
  }

  const handleSuspendDomain = async (domainId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/chat-sdk/domains/${domainId}/suspend`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        toast.success('Domain suspended')
        fetchDomains()
      }
    } catch (e) {
      toast.error('Error: ' + String(e))
    }
  }

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied API key')
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 1500)
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">SDK</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Chat Widget Domain Control</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Register domains, issue embed keys, and govern access for external chat surfaces.
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
            Integration Blueprint
          </CardTitle>
          <CardDescription>
            Add this snippet before your site&apos;s closing body tag.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-xl border border-border/60 bg-slate-900 p-4 text-xs text-slate-100">
{`<script>
  window.RAZE_CONFIG = {
    apiKey: 'your-api-key-here',
    apiUrl: 'https://your-raze-url.com',
    position: 'bottom-right',
    theme: '#0F766E'
  };
</script>
<script src="https://your-raze-url.com/raze-chat-widget.js"></script>`}
          </pre>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registered Domains</CardTitle>
          <CardDescription>Approve and monitor all hosted chat widget origins.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading domains...</p>
          ) : domains.length === 0 ? (
            <p className="text-sm text-muted-foreground">No domains registered yet.</p>
          ) : (
            <div className="space-y-4">
              {domains.map((domain) => (
                <div key={domain.id} className="rounded-xl border border-border/70 p-4">
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

                  {domain.api_key && (
                    <div className="mt-3 rounded-lg border border-border/70 bg-secondary/30 p-3">
                      <p className="mb-1 text-xs text-muted-foreground">API Key</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="min-w-0 flex-1 break-all text-xs">{domain.api_key}</code>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(domain.api_key!, domain.id)}
                        >
                          <Copy className="mr-1.5 h-3.5 w-3.5" />
                          {copiedKey === domain.id ? 'Copied' : 'Copy'}
                        </Button>
                      </div>
                    </div>
                  )}

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>
                      Last used:{' '}
                      {domain.last_used ? new Date(domain.last_used).toLocaleString() : 'Never'}
                    </span>
                    <div className="flex gap-2">
                      {domain.status === 'pending' && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleApproveDomain(domain.id)}
                        >
                          <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                          Approve
                        </Button>
                      )}
                      {domain.status === 'approved' && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="destructive" size="sm">
                              Suspend
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Suspend this domain?</AlertDialogTitle>
                              <AlertDialogDescription>
                                Chat widget traffic from this domain will be blocked until re-approved.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => handleSuspendDomain(domain.id)}>
                                Suspend Domain
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                    </div>
                  </div>
                </div>
              ))}
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
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
            />
            <Input
              placeholder="Display name"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
            />
            <Textarea
              placeholder="Description (optional)"
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewDomain(false)}>
              Cancel
            </Button>
            <Button onClick={handleRegisterDomain}>Register</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
