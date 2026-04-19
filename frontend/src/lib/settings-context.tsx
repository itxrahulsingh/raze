'use client'
import { createContext, useContext, useEffect, useState } from 'react'

interface WhiteLabelSettings {
  brand_name: string
  brand_color: string
  logo_url: string | null
}

interface SettingsContextType {
  whiteLabelSettings: WhiteLabelSettings
  loading: boolean
}

const defaultSettings: WhiteLabelSettings = {
  brand_name: 'RAZE',
  brand_color: '#3B82F6',
  logo_url: null,
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
        // Try new database-backed endpoint first (no auth required)
        const res = await fetch('/api/v1/settings')

        if (res.ok) {
          const data = await res.json()
          setWhiteLabelSettings({
            brand_name: data.brand_name || 'RAZE',
            brand_color: data.brand_color || '#3B82F6',
            logo_url: data.logo_url || null,
          })
        } else {
          // Fallback to defaults
          setWhiteLabelSettings(defaultSettings)
        }
      } catch (e) {
        console.error('Failed to load settings:', e)
        setWhiteLabelSettings(defaultSettings)
      } finally {
        setLoading(false)
      }
    }

    fetchSettings()
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
