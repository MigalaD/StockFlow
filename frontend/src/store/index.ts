/**
 * StockFlow Global Store (Zustand)
 * Poprawiona obsługa SSR — czeka na hydratację przed sprawdzeniem auth.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { authApi } from '../lib/api'

// ── Auth store ────────────────────────────────────────────────────────

interface AuthState {
  token:        string | null
  userId:       string | null
  isAuth:       boolean
  _hasHydrated: boolean
  setHydrated:  () => void
  login:        (username: string, password: string) => Promise<void>
  register:     (username: string, password: string, email?: string) => Promise<void>
  logout:       () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:        null,
      userId:       null,
      isAuth:       false,
      _hasHydrated: false,

      setHydrated: () => set({ _hasHydrated: true }),

      login: async (username, password) => {
        const data = await authApi.login(username, password)
        if (typeof window !== 'undefined') {
          localStorage.setItem('sf_token', data.access_token)
        }
        set({
          token:  data.access_token,
          userId: data.user_id,
          isAuth: true,
        })
      },

      register: async (username, password, email) => {
        const data = await authApi.register(username, password, email)
        if (typeof window !== 'undefined') {
          localStorage.setItem('sf_token', data.access_token)
        }
        set({
          token:  data.access_token,
          userId: data.user_id,
          isAuth: true,
        })
      },

      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('sf_token')
          localStorage.removeItem('sf_user')
        }
        set({ token: null, userId: null, isAuth: false })
      },
    }),
    {
      name:    'sf-auth',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : ({
          getItem:    () => null,
          setItem:    () => {},
          removeItem: () => {},
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any)
      ),
      partialize: (state) => ({
        token:  state.token,
        userId: state.userId,
        isAuth: state.isAuth,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated()
      },
    },
  ),
)


// ── Settings store ────────────────────────────────────────────────────

type Theme  = 'dark' | 'light'
type Locale = 'pl' | 'en'

interface SettingsState {
  theme:     Theme
  locale:    Locale
  setTheme:  (theme: Theme) => void
  setLocale: (locale: Locale) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme:  'dark',
      locale: 'pl',

      setTheme: (theme) => {
        set({ theme })
        if (typeof document !== 'undefined') {
          document.documentElement.classList.toggle('dark', theme === 'dark')
        }
      },

      setLocale: (locale) => {
        set({ locale })
        if (typeof document !== 'undefined') {
          document.cookie = `locale=${locale};path=/;max-age=31536000;SameSite=Lax`
        }
      },
    }),
    {
      name:    'sf-settings',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : ({
          getItem:    () => null,
          setItem:    () => {},
          removeItem: () => {},
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any)
      ),
    },
  ),
)


// ── Recently viewed store ─────────────────────────────────────────────

interface RecentState {
  tickers:     string[]
  addTicker:   (ticker: string) => void
  clearTickers:() => void
}

export const useRecentStore = create<RecentState>()(
  persist(
    (set, get) => ({
      tickers: [],
      addTicker: (ticker) => {
        const current = get().tickers.filter(t => t !== ticker)
        set({ tickers: [ticker, ...current].slice(0, 5) })
      },
      clearTickers: () => set({ tickers: [] }),
    }),
    {
      name:    'sf-recent',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : ({
          getItem:    () => null,
          setItem:    () => {},
          removeItem: () => {},
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any)
      ),
    },
  ),
)


// ── Scanner store ─────────────────────────────────────────────────────

interface ScannerState {
  mode:      'dt' | 'st'
  market:    string
  setMode:   (mode: 'dt' | 'st') => void
  setMarket: (market: string) => void
}

export const useScannerStore = create<ScannerState>()((set) => ({
  mode:      'dt',
  market:    'usa',
  setMode:   (mode)   => set({ mode }),
  setMarket: (market) => set({ market }),
}))
