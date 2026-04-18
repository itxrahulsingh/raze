'use client'

import { useEffect, useMemo, useState } from 'react'
import { Plus, Users, ShieldCheck, Clock3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface UserItem {
  id: string
  email: string
  role?: string
  is_active?: boolean
  last_login?: string | null
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/users', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(Array.isArray(data) ? data : data.items || [])
      }
    } catch {
      // keep stable fallback
    } finally {
      setLoading(false)
    }
  }

  const stats = useMemo(() => {
    const total = users.length
    const active = users.filter((u) => u.is_active).length
    const admins = users.filter((u) => (u.role || '').toLowerCase().includes('admin')).length
    return { total, active, admins }
  }, [users])

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Identity</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">Users & Access Roles</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Monitor user health, role distribution, and account activity across the admin system.
            </p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create User
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
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
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Directory</CardTitle>
          <CardDescription>Account status, role, and login recency.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading users...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground">No users found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">User</th>
                    <th className="py-2 pr-4 font-medium">Role</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 font-medium">Last Login</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-border/60">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="rounded-lg bg-secondary p-1.5">
                            <Users className="h-3.5 w-3.5 text-primary" />
                          </div>
                          <span>{u.email}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant="outline">{u.role || 'user'}</Badge>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={u.is_active ? 'success' : 'secondary'}>
                          <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <span className="inline-flex items-center text-muted-foreground">
                          <Clock3 className="mr-1.5 h-3.5 w-3.5" />
                          {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
