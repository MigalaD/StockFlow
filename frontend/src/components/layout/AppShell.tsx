'use client'

import { type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { Search } from 'lucide-react'
import { Sidebar }    from './Sidebar'
import { TickerTape } from './TickerTape'
import { LanguageSwitcher } from '../shared/LanguageSwitcher'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const router = useRouter()

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-base">
      {/* Ticker tape — sygnatura produktu */}
      <TickerTape />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-auto bg-base">
          {/* Top bar */}
          <div className="sticky top-0 z-30 flex items-center gap-3 px-6 py-2.5 border-b border-border"
            style={{ background: 'rgba(8,12,22,0.85)', backdropFilter: 'blur(12px)' }}>

            {/* Quick search trigger */}
            <button
              onClick={() => router.push('/analysis')}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-surface-1 border border-border
                         text-muted hover:text-text-lo hover:border-border-hi transition-all text-sm w-64 group"
            >
              <Search className="w-4 h-4" />
              <span className="flex-1 text-left">Szukaj instrumentu…</span>
              <kbd className="text-2xs px-1.5 py-0.5 rounded bg-surface-2 border border-border font-mono">⏎</kbd>
            </button>

            <div className="flex-1" />

            <LanguageSwitcher />
          </div>

          {/* Page content */}
          <div className="p-6 animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
