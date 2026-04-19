'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Clock3, RefreshCcw, Search, ShieldCheck, Users } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

interface UserItem {
  id: string
  email: string
  username: string
  full_name?: string | null
  role?: string
  is_active?: boolean
  is_verified?: boolean
  last_login?: string | null
  created_at?: string
}

const PAGE_SIZE = 20

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('access_token')
      const params = new URLSearchParams()
      params.set('limit', String(PAGE_SIZE))
      params.set('offset', String((page - 1) * PAGE_SIZE))
      if (query.trim()) params.set('q', query.trim())
      if (roleFilter !== 'all') params.set('role', roleFilter)

      const res = await fetch(`/api/v1/admin/users?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) throw new Error(`Failed to load users (${res.status})`)
      const payload = await res.json()
      setUsers(payload.items || [])
      setTotal(payload.total || 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
      setUsers([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [page, query, roleFilter])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const stats = useMemo(() => {
    const active = users.filter((user) => user.is_active).length
    const admins = users.filter((user) => (user.role || '').toLowerCase().includes('admin')).length
    const verified = users.filter((user) => user.is_verified).length
    return { total, active, admins, verified }
  }, [total, users])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Identity</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Users & Access Roles</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Search, filter, and audit account health across your admin surface.
            </p>
          </div>
          <Button variant="outline" onClick={fetchUsers} disabled={loading}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Users</CardDescription>
            <CardTitle className="text-3xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Accounts</CardDescription>
            <CardTitle className="text-3xl">{stats.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Admin Roles</CardDescription>
            <CardTitle className="text-3xl">{stats.admins}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Verified</CardDescription>
            <CardTitle className="text-3xl">{stats.verified}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Directory</CardTitle>
          <CardDescription>Role, account status, and login recency.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_220px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search email, username, or full name..."
                value={query}
                onChange={(event) => {
                  setPage(1)
                  setQuery(event.target.value)
                }}
              />
            </div>
            <Select
              value={roleFilter}
              onChange={(event) => {
                setPage(1)
                setRoleFilter(event.target.value)
              }}
            >
              <option value="all">All roles</option>
              <option value="superadmin">Superadmin</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </Select>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading users...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground">No users found for current filters.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="rounded-lg bg-secondary p-1.5">
                          <Users className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{user.full_name || user.username || user.email}</p>
                          <p className="text-xs text-muted-foreground">{user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{user.role || 'viewer'}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Badge variant={user.is_active ? 'success' : 'secondary'}>
                          <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                          {user.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <Badge variant={user.is_verified ? 'success' : 'outline'}>
                          {user.is_verified ? 'Verified' : 'Unverified'}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center text-muted-foreground">
                        <Clock3 className="mr-1.5 h-3.5 w-3.5" />
                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          <div className="flex items-center justify-between">
            <Button variant="outline" size="sm" onClick={() => setPage((prev) => Math.max(1, prev - 1))} disabled={page === 1}>
              Prev
            </Button>
            <span className="text-xs text-muted-foreground">
              Page {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
