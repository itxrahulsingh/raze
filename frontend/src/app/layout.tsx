import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'
import { TokenExpiryWarning } from '@/components/token-expiry-warning'

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
    <html lang="en">
      <body className="font-body">
        <AuthProvider>
          <TokenExpiryWarning />
          <div className="min-h-screen">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  )
}
