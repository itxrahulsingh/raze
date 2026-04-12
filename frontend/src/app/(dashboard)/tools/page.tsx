'use client'
import { useEffect, useState } from 'react'

export default function ToolsPage() {
  const [tools, setTools] = useState([])

  useEffect(() => {
    fetchTools()
  }, [])

  const fetchTools = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/tools', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setTools(await res.json())
    } catch (e) {
      console.error('Failed to fetch tools')
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Tool Management</h1>
      <button className="bg-blue-600 text-white px-4 py-2 rounded mb-6">+ Create Tool</button>
      <div className="grid grid-cols-2 gap-4">
        {tools.length > 0 ? (
          tools.map((tool: any) => (
            <div key={tool.id} className="bg-white p-4 rounded-lg shadow">
              <h3 className="font-bold text-lg">{tool.name}</h3>
              <p className="text-gray-600 text-sm mb-2">{tool.description}</p>
              <p className="text-sm"><span className="font-semibold">Type:</span> {tool.type}</p>
              <p className="text-sm"><span className="font-semibold">Usage:</span> {tool.usage_count}</p>
              <p className="text-sm"><span className="font-semibold">Success Rate:</span> {(tool.success_rate * 100).toFixed(1)}%</p>
            </div>
          ))
        ) : (
          <p className="text-gray-600">No tools created</p>
        )}
      </div>
    </div>
  )
}
