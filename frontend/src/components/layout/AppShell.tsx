'use client'

import { type ReactNode } from 'react'
import { Sidebar }    from './Sidebar'
import { TickerTape } from './TickerTape'
import { LanguageSwitcher } from '../shared/LanguageSwitcher'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface-lo">
      {/* Ticker tape — sygnatura produktu */}
      <TickerTape />

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        {/* Content area */}
        <main className="flex-1 overflow-auto bg-surface-lo animate-fade-in">
          {/* Top bar */}
          <div
            className="sticky top-0 z-10 flex justify-end items-center px-6 py-2 border-b border-border"
            style={{ backgroundColor: 'rgba(11,17,32,0.92)', backdropFilter: 'blur(8px)' }}
          >
            <LanguageSwitcher />
          </div>

          {/* Page content */}
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
