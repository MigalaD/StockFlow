'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useAuthStore } from '../../store'
import { Input, Button } from '../../components/ui'
import { ApiError } from '../../lib/api'

type Mode = 'login' | 'register'

export default function LoginPage() {
  const t      = useTranslations('auth')
  const router = useRouter()
  const { login, register } = useAuthStore()

  const [mode,     setMode]     = useState<Mode>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email,    setEmail]    = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(username, password, email || undefined)
      }
      router.replace('/')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 401 ? t('invalidCreds') :
          err.status === 409 ? t('usernameTaken') :
          err.detail,
        )
      } else {
        setError('Błąd połączenia z serwerem')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: '#0B1120' }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="font-bold text-3xl tracking-tight mb-1">
            <span style={{ color: '#22C55E' }}>Stock</span>
            <span style={{ color: '#14B8A6' }}>Flow</span>
          </div>
          <div className="text-sm text-muted">
            {mode === 'login' ? 'Zaloguj się do swojego konta' : 'Utwórz nowe konto'}
          </div>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-xl2 p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label={t('username')}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="np. damian"
              autoComplete="username"
              required
              minLength={2}
            />
            <Input
              label={t('password')}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              minLength={8}
              hint={mode === 'register' ? t('passwordMin') : undefined}
            />
            {mode === 'register' && (
              <Input
                label={t('email')}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            )}

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full mt-1">
              {mode === 'login' ? t('login') : t('register')}
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-border text-center">
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-muted hover:text-brand-green transition-colors"
            >
              {mode === 'login'
                ? 'Nie masz konta? Zarejestruj się'
                : 'Masz już konto? Zaloguj się'
              }
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-muted mt-6 leading-relaxed">
          StockFlow jest narzędziem edukacyjnym i nie stanowi porady inwestycyjnej.
        </p>
      </div>
    </div>
  )
}
