'use client'

import { useEffect, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '../../store'
import { Spinner } from '../ui'

/**
 * AuthGuard — czeka na hydratację Zustand ORAZ weryfikację tokenu
 * względem backendu, zanim podejmie decyzję o przekierowaniu.
 *
 * Dwa różne problemy, dwie flagi:
 * 1. _hasHydrated   — czy localStorage został w ogóle odczytany (SSR vs client)
 * 2. sessionVerified — czy token (jeśli jest) został potwierdzony jako ważny
 *    przez backend (/auth/me). Sama OBECNOŚĆ tokenu w localStorage nie
 *    znaczy, że jest ważny — może być przeterminowany albo unieważniony
 *    przez rotację SECRET_KEY na serwerze. Bez tej weryfikacji isAuth
 *    kłamie: mówi "zalogowany" mimo że każde żądanie dostanie 401.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuth, _hasHydrated, sessionVerified } = useAuthStore()
  const router = useRouter()

  const ready = _hasHydrated && sessionVerified

  useEffect(() => {
    if (ready && !isAuth) {
      router.replace('/login')
    }
  }, [isAuth, ready, router])

  // Jeszcze nie wiemy na pewno czy zalogowany (hydratacja lub weryfikacja w toku)
  if (!ready || !isAuth) {
    return (
      <div className="flex items-center justify-center h-screen"
           style={{ background: '#0B1120' }}>
        <Spinner size="lg" />
      </div>
    )
  }

  return <>{children}</>
}
