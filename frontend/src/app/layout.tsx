import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'
import { TokenExpiryWarning } from '@/components/token-expiry-warning'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { SettingsProvider } from '@/contexts/SettingsContext'
import RootLayoutClient from './layout-client'

export const metadata: Metadata = {
  title: 'RAZE Admin Dashboard',
  description: 'Enterprise AI OS Control Panel',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-body">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <SettingsProvider>
            <AuthProvider>
              <TokenExpiryWarning />
              <Toaster />
              <RootLayoutClient>
                <div className="min-h-screen">
                  {children}
                </div>
              </RootLayoutClient>
            </AuthProvider>
          </SettingsProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
