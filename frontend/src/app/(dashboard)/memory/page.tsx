'use client'
import { useEffect, useState } from 'react'

export default function MemoryPage() {
  const [memories, setMemories] = useState([])

  useEffect(() => {
    fetchMemories()
  }, [])

  const fetchMemories = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/memory?user_id=user-001', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setMemories(await res.json())
    } catch (e) {
      console.error('Failed to fetch memories')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Memory Management</h1>
      <div className="bg-white p-6 rounded-lg shadow">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b">
              <th className="pb-2">Type</th>
              <th className="pb-2">Content</th>
              <th className="pb-2">Importance</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {memories.length > 0 ? (
              memories.map((m: any) => (
                <tr key={m.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{m.type}</td>
                  <td>{m.content.substring(0, 50)}...</td>
                  <td>
                    <div className="w-20 bg-gray-200 rounded h-2">
                      <div className="bg-blue-600 h-2 rounded" style={{width: `${m.importance_score * 100}%`}} />
                    </div>
                  </td>
                  <td><span className={`${m.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100'} px-2 py-1 rounded`}>{m.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-4 text-center text-gray-600">No memories</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
