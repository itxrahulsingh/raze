'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Clock3, Edit, Plus, RefreshCcw, Search, Shield, Trash2, Users } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

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
  const [createOpen, setCreateOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserItem | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
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
  }, [page, query, roleFilter, token])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const stats = useMemo(() => {
    const active = total > 0 ? users.filter((user) => user.is_active).length : 0
    const admins = total > 0 ? users.filter((user) => user.role === 'admin' || user.role === 'superadmin').length : 0
    const verified = total > 0 ? users.filter((user) => user.is_verified).length : 0
    return { total, active, admins, verified }
  }, [total, users])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData)

    try {
      const res = await fetch('/api/v1/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          email: data.email,
          username: data.username,
          password: data.password,
          full_name: data.full_name || null,
          role: data.role || 'viewer',
        }),
      })
      if (!res.ok) {
        const err = await res.text()
        throw new Error(err)
      }
      toast.success('User created successfully')
      setCreateOpen(false)
      setPage(1)
      fetchUsers()
    } catch (err) {
      toast.error(`Failed to create user: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleUpdate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editingUser) return

    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData)

    try {
      const res = await fetch(`/api/v1/admin/users/${editingUser.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          full_name: data.full_name || null,
          role: data.role,
          is_active: data.is_active === 'on',
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('User updated successfully')
      setEditOpen(false)
      fetchUsers()
    } catch (err) {
      toast.error(`Failed to update user: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (userId: string, userEmail: string) => {
    if (!window.confirm(`Are you sure you want to delete user "${userEmail}"? They will no longer be able to login.`)) return

    try {
      const res = await fetch(`/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to delete user')
      toast.success('User deleted successfully')
      fetchUsers()
    } catch (err) {
      toast.error(`Failed to delete user: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="dashboard-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Identity</p>
            <h2 className="mt-2 text-3xl font-display font-semibold">User Management</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Create, manage, and control user access across the platform.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchUsers} disabled={loading}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Invite User
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite New User</DialogTitle>
                  <DialogDescription>Create a new user account</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreate} className="space-y-4">
                  <input type="email" name="email" placeholder="Email address" required className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <input type="text" name="username" placeholder="Username" required pattern="[a-zA-Z0-9_]{3,}" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <input type="password" name="password" placeholder="Password (min 8 chars)" required minLength={8} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <input type="text" name="full_name" placeholder="Full name (optional)" className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                  <select name="role" defaultValue="viewer" className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                    <option value="viewer">Viewer</option>
                    <option value="admin">Admin</option>
                    <option value="superadmin">Superadmin</option>
                  </select>
                  <Button type="submit" className="w-full">Create User</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
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
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl">{stats.active}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Admins</CardDescription>
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
          <CardTitle>Users</CardTitle>
          <CardDescription>Manage user accounts and permissions.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[250px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value)
                  setPage(1)
                }}
                placeholder="Search by email, username..."
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value)
                setPage(1)
              }}
              className="rounded border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="all">All Roles</option>
              <option value="superadmin">Superadmin</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading users...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground">No users found.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Username</TableHead>
                      <TableHead>Full Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell>{user.username}</TableCell>
                        <TableCell className="text-muted-foreground">{user.full_name || '—'}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              user.role === 'superadmin'
                                ? 'outline'
                                : user.role === 'admin'
                                  ? 'default'
                                  : 'secondary'
                            }
                          >
                            <Shield className="mr-1 h-3 w-3" />
                            {user.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {user.is_active ? (
                              <Badge variant="success">Active</Badge>
                            ) : (
                              <Badge variant="secondary">Inactive</Badge>
                            )}
                            {user.is_verified && <Badge variant="outline">Verified</Badge>}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Dialog open={editOpen && editingUser?.id === user.id} onOpenChange={(open) => { if (open) setEditingUser(user); setEditOpen(open) }}>
                              <DialogTrigger asChild>
                                <Button size="sm" variant="outline" onClick={() => setEditingUser(user)}>
                                  <Edit className="mr-1 h-3.5 w-3.5" />
                                  Edit
                                </Button>
                              </DialogTrigger>
                              <DialogContent>
                                <DialogHeader>
                                  <DialogTitle>Edit User</DialogTitle>
                                </DialogHeader>
                                {editingUser && (
                                  <form onSubmit={handleUpdate} className="space-y-4">
                                    <div>
                                      <p className="text-xs text-muted-foreground mb-2">Email</p>
                                      <p className="font-mono text-sm">{editingUser.email}</p>
                                    </div>
                                    <input type="text" name="full_name" placeholder="Full name" defaultValue={editingUser.full_name || ''} className="w-full rounded border border-input bg-background px-3 py-2 text-sm" />
                                    <select name="role" defaultValue={editingUser.role || 'viewer'} className="w-full rounded border border-input bg-background px-3 py-2 text-sm">
                                      <option value="viewer">Viewer</option>
                                      <option value="admin">Admin</option>
                                      <option value="superadmin">Superadmin</option>
                                    </select>
                                    <div className="flex items-center gap-2">
                                      <input type="checkbox" name="is_active" id="is_active" defaultChecked={editingUser.is_active} className="h-4 w-4 rounded border-input" />
                                      <label htmlFor="is_active" className="text-sm">Active</label>
                                    </div>
                                    <Button type="submit" className="w-full">Update User</Button>
                                  </form>
                                )}
                              </DialogContent>
                            </Dialog>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDelete(user.id, user.email)}
                            >
                              <Trash2 className="mr-1 h-3.5 w-3.5" />
                              Delete
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages} ({total} total)
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage(Math.max(1, page - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
