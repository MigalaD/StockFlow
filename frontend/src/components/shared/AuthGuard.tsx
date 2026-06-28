'use client'

import { useEffect, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '../../store'
import { Spinner } from '../ui'

/**
 * AuthGuard — czeka na hydratację Zustand zanim sprawdzi auth.
 * 
 * Problem bez tego: Next.js SSR renderuje komponent zanim localStorage
 * zostanie odczytany → isAuth = false → redirect do /login → pętla.
 * 
 * Rozwiązanie: _hasHydrated flag ustawiana przez onRehydrateStorage.
 * Dopóki false → pokazuj spinner zamiast redirectować.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuth, _hasHydrated } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    // Czekaj na hydratację — dopiero potem sprawdź czy zalogowany
    if (_hasHydrated && !isAuth) {
      router.replace('/login')
    }
  }, [isAuth, _hasHydrated, router])

  // Jeszcze nie wiemy czy zalogowany — pokaż spinner
  if (!_hasHydrated) {
    return (
      <div className="flex items-center justify-center h-screen"
           style={{ background: '#0B1120' }}>
        <Spinner size="lg" />
      </div>
    )
  }

  // Wiemy że NIE jest zalogowany — nic nie renderuj (redirect w toku)
  if (!isAuth) {
    return (
      <div className="flex items-center justify-center h-screen"
           style={{ background: '#0B1120' }}>
        <Spinner size="lg" />
      </div>
    )
  }

  return <>{children}</>
}
