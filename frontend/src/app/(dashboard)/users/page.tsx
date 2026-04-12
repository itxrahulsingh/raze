'use client'
import { useEffect, useState } from 'react'

export default function UsersPage() {
  const [users, setUsers] = useState([])

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/admin/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setUsers(await res.json())
    } catch (e) {
      console.error('Failed to fetch users')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Users</h1>
      <button className="bg-blue-600 text-white px-4 py-2 rounded mb-6">+ Create User</button>
      <div className="bg-white p-6 rounded-lg shadow">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b">
              <th className="pb-2">Email</th>
              <th className="pb-2">Role</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Last Login</th>
            </tr>
          </thead>
          <tbody>
            {users.length > 0 ? (
              users.map((u: any) => (
                <tr key={u.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{u.email}</td>
                  <td><span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm">{u.role}</span></td>
                  <td><span className={`${u.is_active ? 'text-green-600' : 'text-gray-600'}`}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td>{u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-4 text-center text-gray-600">No users</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
