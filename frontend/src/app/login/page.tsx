'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { TrendingUp, ShieldCheck, BarChart3, Bell } from 'lucide-react'
import { useAuthStore } from '../../store'
import { Input, Button } from '../../components/ui'
import { ApiError } from '../../lib/api'

type Mode = 'login' | 'register'

const FEATURES = [
  { icon: BarChart3,   text: 'Analiza score dla akcji, ETF, krypto i surowców' },
  { icon: TrendingUp,  text: 'Scenariusze cenowe Monte Carlo i backtesting' },
  { icon: Bell,        text: 'Alerty Telegram gdy score przekroczy próg' },
  { icon: ShieldCheck, text: 'Twoje dane szyfrowane, bez reklam' },
]

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
        setError('Nie udało się połączyć z serwerem. Spróbuj ponownie.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: '#080C16' }}>

      {/* Left — branding panel (desktop only) */}
      <div className="hidden lg:flex flex-col justify-between w-[44%] p-12 relative overflow-hidden border-r border-border">
        {/* Ambient gradient */}
        <div className="absolute inset-0 opacity-30 pointer-events-none"
          style={{ background: 'radial-gradient(circle at 30% 20%, rgba(34,197,94,0.15), transparent 50%), radial-gradient(circle at 70% 80%, rgba(20,184,166,0.12), transparent 50%)' }} />

        {/* Logo */}
        <div className="relative">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #22C55E, #14B8A6)' }}>
              <TrendingUp className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-bold text-2xl text-logo">StockFlow</span>
          </div>
          <div className="text-2xs text-muted tracking-[0.16em] uppercase mt-2 ml-[52px]">
            Market Analytics
          </div>
        </div>

        {/* Value prop */}
        <div className="relative">
          <h1 className="text-3xl font-bold text-text-hi leading-tight tracking-tight mb-2">
            Analizuj rynki<br/>jak profesjonalista.
          </h1>
          <p className="text-text-lo text-sm leading-relaxed mb-8 max-w-sm">
            Kompleksowa platforma do analizy technicznej i fundamentalnej — w jednym,
            przejrzystym narzędziu po polsku.
          </p>

          <div className="space-y-3.5">
            {FEATURES.map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(34,197,94,0.12)' }}>
                  <Icon className="w-4 h-4 text-brand-green" />
                </div>
                <span className="text-sm text-text-mid">{text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-2xs text-muted">
          © 2026 StockFlow · Narzędzie edukacyjne, nie porada inwestycyjna
        </div>
      </div>

      {/* Right — form */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-sm animate-slide-up">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="font-bold text-3xl tracking-tight text-logo">StockFlow</div>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-text-hi tracking-tight">
              {mode === 'login' ? 'Witaj ponownie' : 'Utwórz konto'}
            </h2>
            <p className="text-sm text-text-lo mt-1">
              {mode === 'login'
                ? 'Zaloguj się aby kontynuować analizę'
                : 'Bezpłatne konto — zacznij w 30 sekund'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label={t('username')}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="np. damian"
              autoComplete="username"
              required minLength={2}
            />
            <Input
              label={t('password')}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required minLength={8}
              hint={mode === 'register' ? t('passwordMin') : undefined}
            />
            {mode === 'register' && (
              <Input
                label={`${t('email')} (opcjonalnie)`}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                hint="Potrzebny tylko do alertów e-mail"
              />
            )}

            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5 animate-fade-in">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} size="lg" className="w-full mt-1">
              {mode === 'login' ? t('login') : t('register')}
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-border text-center">
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-text-lo hover:text-brand-green transition-colors"
            >
              {mode === 'login'
                ? <>Nie masz konta? <span className="font-semibold text-brand-green">Zarejestruj się</span></>
                : <>Masz już konto? <span className="font-semibold text-brand-green">Zaloguj się</span></>
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
