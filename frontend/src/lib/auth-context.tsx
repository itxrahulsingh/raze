'use client'
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  user: any | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  isTokenExpiring: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<any | null>(null)
  const [isTokenExpiring, setIsTokenExpiring] = useState(false)
  const [expiresIn, setExpiresIn] = useState<number | null>(null)

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    const storedExpiresIn = localStorage.getItem('token_expires_in')

    if (storedToken) {
      setToken(storedToken)
      setIsAuthenticated(true)
      if (storedExpiresIn) {
        setExpiresIn(parseInt(storedExpiresIn))
      }
      // Fetch current user
      fetchCurrentUser(storedToken)
    }
  }, [])

  // Monitor token expiration
  useEffect(() => {
    if (!expiresIn || !isAuthenticated) return

    const interval = setInterval(() => {
      setExpiresIn(prev => {
        if (!prev) return null
        const newExpiresIn = prev - 1

        // Warn when 5 minutes remaining
        if (newExpiresIn === 300) {
          setIsTokenExpiring(true)
        }

        // Auto-logout when expired
        if (newExpiresIn <= 0) {
          logout()
          return null
        }

        // Try refresh when 2 minutes remaining
        if (newExpiresIn === 120) {
          refreshToken().catch(() => {
            logout()
          })
        }

        return newExpiresIn
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [expiresIn, isAuthenticated])

  const fetchCurrentUser = async (authToken: string) => {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 3000)

      const res = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${authToken}` },
        signal: controller.signal
      })
      clearTimeout(timeout)

      if (res.ok) {
        const userData = await res.json()
        setUser(userData)
      } else if (res.status === 401) {
        logout()
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        console.warn('Auth check timeout - continuing with stored token')
      } else {
        console.error('Failed to fetch current user:', e)
      }
    }
  }

  const login = useCallback(async (email: string, password: string) => {
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      if (!res.ok) {
        throw new Error('Login failed')
      }

      const data = await res.json()
      const accessToken = data.access_token
      const expiresIn = data.expires_in || 3600 // Default 1 hour

      // Store token and expiry
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('token_expires_in', String(expiresIn))
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      setToken(accessToken)
      setExpiresIn(expiresIn)
      setIsAuthenticated(true)
      setIsTokenExpiring(false)

      // Fetch user data
      await fetchCurrentUser(accessToken)

      // Navigate to dashboard
      router.push('/dashboard')
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }, [router])

  const refreshToken = useCallback(async () => {
    try {
      const refreshTokenValue = localStorage.getItem('refresh_token')
      if (!refreshTokenValue) {
        throw new Error('No refresh token available')
      }

      const res = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshTokenValue })
      })

      if (!res.ok) {
        throw new Error('Token refresh failed')
      }

      const data = await res.json()
      const accessToken = data.access_token
      const expiresIn = data.expires_in || 3600

      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('token_expires_in', String(expiresIn))
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }

      setToken(accessToken)
      setExpiresIn(expiresIn)
      setIsTokenExpiring(false)

      console.log('Token refreshed successfully')
    } catch (error) {
      console.error('Token refresh error:', error)
      logout()
      throw error
    }
  }, [])

  const logout = useCallback(() => {
    // Clear storage
    localStorage.removeItem('access_token')
    localStorage.removeItem('token_expires_in')
    localStorage.removeItem('refresh_token')

    // Clear state
    setToken(null)
    setUser(null)
    setIsAuthenticated(false)
    setExpiresIn(null)
    setIsTokenExpiring(false)

    // Navigate to login
    router.push('/login')
  }, [router])

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        token,
        user,
        login,
        logout,
        refreshToken,
        isTokenExpiring
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
