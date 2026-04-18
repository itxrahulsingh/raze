'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import {
  BarChart3,
  Bot,
  BrainCircuit,
  ChevronRight,
  Code2,
  Database,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Settings,
  ShieldCheck,
  Sun,
  Wrench,
  Users,
  MessageSquareText,
  Library,
} from 'lucide-react'
import { SettingsProvider, useSettings } from '@/lib/settings-context'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { useTheme } from 'next-themes'

type NavItem = {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  hint: string
}

const navItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, hint: 'Overview' },
  { name: 'Knowledge', href: '/knowledge', icon: Library, hint: 'Sources' },
  { name: 'Admin Chat', href: '/admin-chat', icon: Bot, hint: 'Agent Console' },
  { name: 'Chat SDK', href: '/chat-sdk', icon: Code2, hint: 'Embed Config' },
  { name: 'Conversations', href: '/conversations', icon: MessageSquareText, hint: 'Threads' },
  { name: 'Memory', href: '/memory', icon: BrainCircuit, hint: 'Context Store' },
  { name: 'Tools', href: '/tools', icon: Wrench, hint: 'Integrations' },
  { name: 'Analytics', href: '/analytics', icon: BarChart3, hint: 'Performance' },
  { name: 'Users', href: '/users', icon: Users, hint: 'Access Control' },
  { name: 'Settings', href: '/settings', icon: Settings, hint: 'Platform' },
]

function DashboardLayoutContent({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const [user, setUser] = useState<{ email?: string } | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [mounted, setMounted] = useState(false)
  const { whiteLabelSettings } = useSettings()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push('/login')
      return
    }
    fetchUser(token)
  }, [router])

  const fetchUser = async (token: string) => {
    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setUser(await res.json())
      } else if (res.status === 401) {
        handleLogout()
      }
    } catch {
      // keep shell usable even if profile fetch fails
    }
  }

  const activeItem = useMemo(
    () => navItems.find((item) => pathname?.startsWith(item.href)) || navItems[0],
    [pathname]
  )

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    router.push('/login')
  }

  const Sidebar = (
    <aside className="flex h-full w-[290px] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex items-start justify-between gap-3 px-5 py-6">
        <div className="flex items-center gap-3">
          {whiteLabelSettings.logo_url ? (
            <img
              src={whiteLabelSettings.logo_url}
              alt="Brand logo"
              className="h-10 w-10 rounded-xl border border-white/20 object-cover"
            />
          ) : (
            <div
              className="grid h-10 w-10 place-items-center rounded-xl text-sm font-bold text-white"
              style={{ backgroundColor: whiteLabelSettings.brand_color }}
            >
              RZ
            </div>
          )}
          <div>
            <p className="font-display text-lg leading-none">{whiteLabelSettings.brand_name}</p>
            <p className="mt-1 text-xs text-sidebar-foreground/70">AI Agent Super Admin</p>
          </div>
        </div>
        <Badge className="rounded-md bg-white/10 text-[10px] uppercase tracking-wide text-white">
          v1
        </Badge>
      </div>

      <Separator className="bg-white/10" />

      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname?.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-all',
                active
                  ? 'bg-white text-slate-900 shadow-md'
                  : 'text-sidebar-foreground/80 hover:bg-white/8 hover:text-white'
              )}
              onClick={() => setSidebarOpen(false)}
            >
              <span className="flex items-center gap-3">
                <Icon className={cn('h-4 w-4', active ? 'text-primary' : 'text-sidebar-foreground/70')} />
                <span>{item.name}</span>
              </span>
              <span className={cn('text-[11px]', active ? 'text-slate-500' : 'text-sidebar-foreground/50 group-hover:text-sidebar-foreground/70')}>
                {item.hint}
              </span>
            </Link>
          )
        })}
      </nav>

      <div className="space-y-4 p-4">
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="flex items-center gap-2 text-xs text-sidebar-foreground/80">
            <ShieldCheck className="h-4 w-4 text-emerald-300" />
            Authenticated Session
          </div>
          <p className="mt-1 truncate text-sm font-medium">{user?.email || 'Loading user...'}</p>
        </div>
        <Button
          variant="destructive"
          className="w-full justify-center rounded-xl"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen">
      <div className="fixed inset-y-0 left-0 z-50 hidden lg:block">{Sidebar}</div>

      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px]"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar overlay"
          />
          <div className="absolute left-0 top-0 h-full">{Sidebar}</div>
        </div>
      )}

      <main className="lg:pl-[290px]">
        <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 sm:gap-3">
              <Button
                variant="outline"
                size="icon"
                className="lg:hidden"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open sidebar"
              >
                <Menu className="h-4 w-4" />
              </Button>
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                  Control Plane
                  <ChevronRight className="h-3.5 w-3.5" />
                  {activeItem.name}
                </div>
                <h1 className="font-display text-lg font-semibold sm:text-xl">{activeItem.hint}</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                aria-label="Toggle theme"
              >
                {mounted && theme === 'dark' ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </Button>
              <div className="hidden items-center gap-2 sm:flex">
              <Badge variant="success">Live</Badge>
              <Badge variant="secondary">
                <Database className="mr-1 h-3.5 w-3.5" />
                Backend Connected
              </Badge>
              </div>
            </div>
          </div>
        </header>

        <section className="animate-rise-in p-4 sm:p-6">{children}</section>
      </main>
    </div>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SettingsProvider>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </SettingsProvider>
  )
}
