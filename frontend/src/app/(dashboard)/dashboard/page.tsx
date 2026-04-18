'use client'

import { useEffect, useMemo, useState } from 'react'
import { Activity, Brain, MessageSquare, Users, Database, ShieldCheck, Clock3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

type DashboardStats = {
  conversations?: number
  messages?: number
  sources?: number
  users?: number
  stats?: {
    total_conversations?: number
    total_users?: number
    total_knowledge_sources?: number
    active_users_today?: number
    redis_connected?: boolean
    avg_latency_ms_today?: number
  }
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({})

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/dashboard', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setStats(await res.json())
      }
    } catch {
      // leave fallback values
    }
  }

  const resolved = useMemo(
    () => ({
      conversations: stats.stats?.total_conversations ?? stats.conversations ?? 0,
      messages: stats.messages ?? 0,
      sources: stats.stats?.total_knowledge_sources ?? stats.sources ?? 0,
      users: stats.stats?.total_users ?? stats.users ?? 0,
      activeToday: stats.stats?.active_users_today ?? 0,
      avgLatency: stats.stats?.avg_latency_ms_today ?? 0,
      redisConnected: stats.stats?.redis_connected ?? true,
    }),
    [stats]
  )

  const cards = [
    {
      title: 'Conversations',
      value: resolved.conversations.toLocaleString(),
      note: 'Active and archived sessions',
      icon: MessageSquare,
      accent: 'from-cyan-500 to-teal-500',
    },
    {
      title: 'Messages',
      value: resolved.messages.toLocaleString(),
      note: 'All message events processed',
      icon: Activity,
      accent: 'from-blue-500 to-indigo-500',
    },
    {
      title: 'Knowledge Sources',
      value: resolved.sources.toLocaleString(),
      note: 'Indexed docs + approved sources',
      icon: Brain,
      accent: 'from-amber-500 to-orange-500',
    },
    {
      title: 'Users',
      value: resolved.users.toLocaleString(),
      note: `${resolved.activeToday.toLocaleString()} active today`,
      icon: Users,
      accent: 'from-fuchsia-500 to-pink-500',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="dashboard-surface relative overflow-hidden p-6">
        <div className="absolute -top-16 right-0 h-48 w-48 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute -bottom-10 left-8 h-36 w-36 rounded-full bg-amber-300/30 blur-2xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-muted-foreground">Super Admin Command Center</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">System Pulse</h2>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              Unified visibility across orchestration, memory, knowledge, and access control.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success">
              <ShieldCheck className="mr-1.5 h-3.5 w-3.5" />
              Platform Healthy
            </Badge>
            <Badge variant="secondary">
              <Clock3 className="mr-1.5 h-3.5 w-3.5" />
              Avg latency {Math.round(resolved.avgLatency)}ms
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <Card key={card.title} className="relative overflow-hidden">
              <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${card.accent}`} />
              <CardHeader className="pb-2">
                <CardDescription className="text-xs uppercase tracking-wide">{card.title}</CardDescription>
                <CardTitle className="text-3xl">{card.value}</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between pt-0">
                <p className="text-sm text-muted-foreground">{card.note}</p>
                <div className="rounded-lg bg-secondary p-2">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Infrastructure Readiness</CardTitle>
            <CardDescription>Critical components for agent runtime reliability.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border/70 bg-secondary/40 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Database</p>
              <p className="mt-2 text-lg font-semibold text-emerald-700">Healthy</p>
            </div>
            <div className="rounded-xl border border-border/70 bg-secondary/40 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Redis</p>
              <p className="mt-2 text-lg font-semibold text-emerald-700">
                {resolved.redisConnected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-secondary/40 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Vector Search</p>
              <p className="mt-2 text-lg font-semibold text-emerald-700">Available</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Runtime Tag</CardTitle>
            <CardDescription>Current deployment profile.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-xl border border-border/70 p-3">
              <span className="text-sm text-muted-foreground">Mode</span>
              <Badge>Production</Badge>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border/70 p-3">
              <span className="text-sm text-muted-foreground">Region</span>
              <span className="text-sm font-medium">ap-south</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border/70 p-3">
              <span className="text-sm text-muted-foreground">Store</span>
              <span className="flex items-center text-sm font-medium">
                <Database className="mr-1.5 h-4 w-4 text-primary" />
                PostgreSQL + pgvector
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
