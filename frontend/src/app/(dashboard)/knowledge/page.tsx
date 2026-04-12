'use client'
import { useState } from 'react'

export default function KnowledgePage() {
  const [sources, setSources] = useState([])
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/knowledge/sources', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })
      if (res.ok) {
        alert('File uploaded successfully!')
      }
    } catch (e) {
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Knowledge Management</h1>
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h2 className="text-xl font-bold mb-4">Upload Document</h2>
        <input
          type="file"
          onChange={handleUpload}
          disabled={uploading}
          accept=".pdf,.docx,.txt"
          className="block w-full"
        />
        {uploading && <p className="text-blue-600">Uploading...</p>}
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Knowledge Sources</h2>
        <p className="text-gray-600">No sources uploaded yet</p>
      </div>
    </div>
  )
}
