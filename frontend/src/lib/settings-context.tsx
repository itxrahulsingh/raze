'use client'
import { createContext, useContext, useEffect, useState } from 'react'

interface WhiteLabelSettings {
  brand_name: string
  brand_color: string
  logo_url: string
}

interface SettingsContextType {
  whiteLabelSettings: WhiteLabelSettings
  loading: boolean
}

const defaultSettings: WhiteLabelSettings = {
  brand_name: 'RAZE',
  brand_color: '#3B82F6',
  logo_url: '',
}

const SettingsContext = createContext<SettingsContextType>({
  whiteLabelSettings: defaultSettings,
  loading: true,
})

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [whiteLabelSettings, setWhiteLabelSettings] = useState<WhiteLabelSettings>(defaultSettings)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const token = localStorage.getItem('access_token')
        if (!token) {
          setLoading(false)
          return
        }

        const res = await fetch('/api/v1/admin/white-label', {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (res.ok) {
          const data = await res.json()
          setWhiteLabelSettings({
            brand_name: data.brand_name || 'RAZE',
            brand_color: data.brand_color || '#3B82F6',
            logo_url: data.logo_url || '',
          })
        }
      } catch (e) {
        console.error('Failed to load settings:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchSettings()
    const interval = setInterval(fetchSettings, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <SettingsContext.Provider value={{ whiteLabelSettings, loading }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  return useContext(SettingsContext)
}
