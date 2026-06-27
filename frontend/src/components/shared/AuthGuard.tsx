'use client'

import { useEffect, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '../../store'
import { Spinner } from '../ui'

/** HOC — wymaga zalogowania. Redirect do /login przy braku tokenu. */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuth } = useAuthStore()
  const router     = useRouter()

  useEffect(() => {
    if (!isAuth) {
      router.replace('/login')
    }
  }, [isAuth, router])

  if (!isAuth) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  return <>{children}</>
}
