'use client'

import { useState, type ReactNode } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar }    from './Sidebar'
import { TickerTape } from './TickerTape'
import { LanguageSwitcher } from '../shared/LanguageSwitcher'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-base">
      {/* Ticker tape — sygnatura produktu */}
      <TickerTape />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

        <main className="flex-1 overflow-auto bg-base min-w-0">
          {/* Top bar */}
          <div className="sticky top-0 z-30 flex items-center gap-3 px-4 lg:px-6 py-2.5 border-b border-border"
            style={{ background: 'rgba(8,12,22,0.85)', backdropFilter: 'blur(12px)' }}>

            {/* Hamburger — tylko mobile */}
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 -ml-1 rounded-lg text-text-lo hover:text-text-hi hover:bg-surface-2 transition-colors"
              aria-label="Otwórz menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex-1" />

            <LanguageSwitcher />
          </div>

          {/* Page content */}
          <div className="p-4 lg:p-6 animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
