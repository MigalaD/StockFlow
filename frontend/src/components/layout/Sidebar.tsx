'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, GitCompare, Star, Briefcase,
  Bitcoin, ScanLine, FlaskConical, BookText, Settings, Info, LogOut, type LucideIcon,
} from 'lucide-react'
import { useAuthStore } from '../../store'

interface NavItem { href: string; icon: LucideIcon; tKey: string }

const NAV_GROUPS: { label: string | null; items: NavItem[] }[] = [
  {
    label: null,
    items: [
      { href: '/',          icon: LayoutDashboard,  tKey: 'dashboard' },
      { href: '/analysis',  icon: TrendingUp,       tKey: 'analysis'  },
      { href: '/compare',   icon: GitCompare, tKey: 'comparison'},
    ],
  },
  {
    label: 'Portfel',
    items: [
      { href: '/watchlist', icon: Star,      tKey: 'watchlist' },
      { href: '/portfolio', icon: Briefcase, tKey: 'portfolio' },
      { href: '/journal',   icon: BookText,  tKey: 'journal'   },
    ],
  },
  {
    label: 'Narzędzia',
    items: [
      { href: '/scanner',  icon: ScanLine,        tKey: 'scanner'  },
      { href: '/backtest', icon: FlaskConical, tKey: 'backtest' },
      { href: '/crypto',   icon: Bitcoin,      tKey: 'crypto'   },
    ],
  },
]

const BOTTOM_ITEMS: NavItem[] = [
  { href: '/settings', icon: Settings, tKey: 'settings' },
  { href: '/about',    icon: Info,     tKey: 'about'    },
]

export function Sidebar({ mobileOpen = false, onClose }: { mobileOpen?: boolean; onClose?: () => void }) {
  const t        = useTranslations('nav')
  const pathname = usePathname()
  const { isAuth, userId, logout } = useAuthStore()

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href)

  const NavLink = ({ href, icon: Icon, tKey }: NavItem) => {
    const active = isActive(href)
    return (
      <Link
        href={href}
        onClick={onClose}
        className={clsx(
          'group flex items-center gap-3 px-3 py-2 rounded-lg mb-0.5 text-sm transition-all relative',
          active ? 'text-text-hi font-semibold' : 'text-text-lo hover:text-text-hi hover:bg-surface-2',
        )}
        style={active ? { background: 'rgba(34,197,94,0.10)' } : undefined}
      >
        {active && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full"
            style={{ background: '#22C55E' }} />
        )}
        <Icon className={clsx('w-[18px] h-[18px] shrink-0 transition-colors',
          active ? 'text-brand-green' : 'text-muted group-hover:text-text-lo')} />
        <span>{t(tKey)}</span>
      </Link>
    )
  }

  return (
    <>
      {/* Nakładka na mobile — przyciemnia treść gdy sidebar otwarty */}
      {mobileOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/60 lg:hidden animate-fade-in"
          aria-hidden="true"
        />
      )}

      <aside className={clsx(
        'w-[228px] shrink-0 flex flex-col h-full border-r border-border bg-surface-1',
        // Desktop: statyczny w przepływie. Mobile: wysuwany panel z lewej.
        'fixed inset-y-0 left-0 z-50 transition-transform duration-300',
        'lg:static lg:translate-x-0 lg:z-auto',
        mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      )}>
        {/* Logo */}
        <div className="px-5 py-[18px] border-b border-border">
          <Link href="/" onClick={onClose} className="block group">
            <div className="font-bold text-xl tracking-tight flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'linear-gradient(135deg, #22C55E, #14B8A6)' }}>
                <TrendingUp className="w-4 h-4 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-logo">StockFlow</span>
            </div>
            <div className="text-2xs text-muted tracking-[0.14em] uppercase mt-1 ml-9">
              Market Analytics
            </div>
          </Link>
        </div>

        {/* Nav groups */}
        <nav className="flex-1 px-2.5 py-3 overflow-y-auto">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi} className={gi > 0 ? 'mt-4' : ''}>
              {group.label && (
                <div className="px-3 mb-1.5 text-2xs font-semibold text-muted uppercase tracking-widest">
                  {group.label}
                </div>
              )}
              {group.items.map(item => <NavLink key={item.href} {...item} />)}
            </div>
          ))}

          <div className="border-t border-border mt-4 pt-3">
            {BOTTOM_ITEMS.map(item => <NavLink key={item.href} {...item} />)}
          </div>
        </nav>

        {/* User block */}
        <div className="px-3 pb-4">
          {isAuth ? (
            <div className="bg-surface-2 border border-border rounded-xl p-3 flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm shrink-0 font-mono"
                style={{ background: 'rgba(34,197,94,0.15)', color: '#22C55E' }}>
                {userId?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-text-hi truncate">{userId}</div>
                <div className="text-2xs text-muted">Zalogowany</div>
              </div>
              <button onClick={logout} title="Wyloguj"
                className="p-1.5 rounded-md text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link href="/login" onClick={onClose} className="btn-secondary w-full">
              Zaloguj się
            </Link>
          )}
        </div>
      </aside>
    </>
  )
}
