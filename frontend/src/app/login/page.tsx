'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTheme } from 'next-themes'
import { Moon, ShieldCheck, Sparkles, Sun, TerminalSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { theme, setTheme } = useTheme()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) throw new Error('Login failed')

      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0 mesh-bg dark:mesh-bg-dark" />
      <div className="absolute -left-24 top-14 h-72 w-72 rounded-full bg-teal-300/30 blur-3xl animate-float-slower" />
      <div className="absolute -right-20 bottom-12 h-80 w-80 rounded-full bg-amber-300/30 blur-3xl animate-float-slow" />

      <Button
        type="button"
        variant="outline"
        size="icon"
        className="absolute right-4 top-4 z-20"
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </Button>

      <Card className="relative z-10 w-full max-w-lg border-border/70 bg-card/85 animate-rise-in">
        <CardHeader className="space-y-4 pb-2">
          <div className="flex items-center justify-between">
            <Badge variant="secondary" className="rounded-full px-3 py-1">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              AI Control Plane
            </Badge>
            <div className="rounded-xl border border-border/70 bg-white/80 p-2">
              <TerminalSquare className="h-5 w-5 text-primary" />
            </div>
          </div>
          <div>
            <CardTitle className="text-3xl">RAZE Super Admin</CardTitle>
            <CardDescription className="mt-2 text-base">
              Secure access to orchestration, analytics, memory, and tool governance.
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@yourcompany.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>
            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}
            <Button type="submit" disabled={loading} className="h-11 w-full text-base">
              {loading ? 'Authenticating...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="h-4 w-4" />
            JWT + refresh token session security enabled
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
