import type { NextConfig } from 'next'
import createNextIntlPlugin from 'next-intl/plugin'

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts')

const nextConfig: NextConfig = {
  // Produkcja: ustaw URL backendu w NEXT_PUBLIC_API_URL
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Optymalizacje
  compress:       true,
  poweredByHeader: false,

  // Obrazy (logo, favicon)
  images: {
    domains: ['localhost'],
    formats: ['image/avif', 'image/webp'],
  },

  // Experimental
  experimental: {
    // Server Components fetch cache
    staleTimes: {
      dynamic: 30,
      static:  180,
    },
  },
}

export default withNextIntl(nextConfig)
