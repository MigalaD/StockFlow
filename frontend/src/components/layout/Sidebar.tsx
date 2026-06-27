'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { clsx } from 'clsx'
import { useAuthStore } from '../../store'

const NAV_ITEMS = [
  { href: '/',          icon: '⊞', key: 'dashboard'  },
  { href: '/analysis',  icon: '↗', key: 'analysis'   },
  { href: '/compare',   icon: '⇆', key: 'comparison' },
  { href: '/watchlist', icon: '★', key: 'watchlist'  },
  { href: '/portfolio', icon: '◈', key: 'portfolio'  },
  { href: '/crypto',    icon: '₿', key: 'crypto'     },
  { href: '/scanner',   icon: '⊙', key: 'scanner'    },
  { href: '/backtest',  icon: '⚗', key: 'backtest'   },
  { href: '/journal',   icon: '📓', key: 'journal'   },
] as const

const BOTTOM_ITEMS = [
  { href: '/settings', icon: '⚙', key: 'settings' },
  { href: '/about',    icon: 'ℹ', key: 'about'    },
] as const

export function Sidebar() {
  const t        = useTranslations('nav')
  const pathname = usePathname()
  const { isAuth, userId, logout } = useAuthStore()

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href)

  return (
    <aside
      className="w-[220px] shrink-0 flex flex-col h-full border-r border-border"
      style={{ backgroundColor: '#111827' }}
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <Link href="/" className="block">
          <div className="font-bold text-xl tracking-tight">
            <span style={{ color: '#22C55E' }}>Stock</span>
            <span style={{ color: '#14B8A6' }}>Flow</span>
          </div>
          <div className="text-[10px] text-muted tracking-[0.12em] uppercase mt-0.5">
            Market Analytics
          </div>
        </Link>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-2.5 py-3 overflow-y-auto">
        {NAV_ITEMS.map(({ href, icon, key }) => {
          const active = isActive(href)
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg mb-0.5',
                'text-sm transition-all',
                active
                  ? 'font-semibold'
                  : 'text-muted hover:text-white hover:bg-surface-hi',
              )}
              style={active ? {
                color:           '#F8FAFC',
                background:      'rgba(34,197,94,0.12)',
                borderLeft:      '3px solid #22C55E',
                paddingLeft:     '9px',
              } : undefined}
            >
              <span className="text-base w-5 text-center">{icon}</span>
              <span>{t(key)}</span>
            </Link>
          )
        })}

        <div className="border-t border-border mt-2 pt-2">
          {BOTTOM_ITEMS.map(({ href, icon, key }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg mb-0.5 text-sm text-muted hover:text-white hover:bg-surface-hi transition-all"
            >
              <span className="text-base w-5 text-center">{icon}</span>
              <span>{t(key)}</span>
            </Link>
          ))}
        </div>
      </nav>

      {/* User block */}
      <div className="px-3 pb-4">
        {isAuth ? (
          <div className="bg-surface-hi rounded-lg p-3 flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
              style={{ background: 'rgba(34,197,94,0.2)', color: '#22C55E' }}
            >
              {userId?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-white truncate">{userId}</div>
              <button
                onClick={logout}
                className="text-[10px] text-muted hover:text-red-400 transition-colors"
              >
                Wyloguj
              </button>
            </div>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg text-sm font-semibold border border-brand-green text-brand-green hover:bg-brand-green/10 transition-all"
          >
            Zaloguj się
          </Link>
        )}
      </div>
    </aside>
  )
}
