import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { NextIntlClientProvider } from 'next-intl'
import { getMessages, getLocale } from 'next-intl/server'
import { ToastProvider } from '../components/shared/ToastProvider'
import './globals.css'

const inter = Inter({
  subsets:  ['latin', 'latin-ext'],
  variable: '--font-inter',
  display:  'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets:  ['latin'],
  variable: '--font-mono',
  display:  'swap',
  weight:   ['400', '500', '600', '700'],
})

export const metadata: Metadata = {
  title: {
    template: '%s | StockFlow',
    default:  'StockFlow – Analityka Rynkowa',
  },
  description:
    'Narzędzie do analizy technicznej i fundamentalnej akcji, ETF-ów, '
    + 'kryptowalut i surowców. Score 0–100, wykresy live, skaner rynku.',
  keywords:   ['analiza techniczna', 'giełda', 'inwestycje', 'stock analysis', 'GPW', 'NYSE'],
  authors:    [{ name: 'Damian Migała' }],
  robots:     'noindex, nofollow',
  manifest:   '/manifest.json',
  appleWebApp: {
    capable:          true,
    statusBarStyle:   'black-translucent',
    title:            'StockFlow',
  },
}

export const viewport: Viewport = {
  width:              'device-width',
  initialScale:       1,
  maximumScale:       1,
  themeColor:         '#1F2937',
  colorScheme:        'dark',
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const locale   = await getLocale()
  const messages = await getMessages()

  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <head>
        {/* Flash fix — ustawia tło zanim CSS się załaduje */}
        <style dangerouslySetInnerHTML={{ __html: `
          html, body { background-color: #0B1120; color: #F8FAFC; }
        `}} />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans bg-surface-lo text-white antialiased`}>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
          <ToastProvider />
        </NextIntlClientProvider>
      </body>
    </html>
  )
}

