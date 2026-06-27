'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useRouter } from 'next/navigation'
import { AppShell } from '../../components/layout/AppShell'
import { Card, SectionHeader, Button, Input } from '../../components/ui'
import { useAuthStore, useSettingsStore } from '../../store'
import { AuthGuard } from '../../components/shared/AuthGuard'

function ThemeToggle() {
  const t = useTranslations('settings')
  const { theme, setTheme } = useSettingsStore()

  return (
    <div>
      <SectionHeader title={t('appearance')} icon="🎨" />
      <div className="flex gap-3">
        {(['dark','light'] as const).map(mode => (
          <button
            key={mode}
            onClick={() => setTheme(mode)}
            className="flex-1 py-3 rounded-xl border text-sm font-semibold transition-all"
            style={{
              background:  theme === mode ? 'rgba(34,197,94,0.15)' : '#1E293B',
              color:       theme === mode ? '#22C55E' : '#64748B',
              borderColor: theme === mode ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.07)',
            }}
          >
            {mode === 'dark' ? '🌙 ' : '☀️ '}
            {t(`theme.${mode}`)}
            {theme === mode && ' ✓'}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted mt-2">
        Zmiana trybu działa w tej sesji przeglądarki. Trwała zmiana zachowuje się w localStorage.
      </p>
    </div>
  )
}

function LanguageSection() {
  const t = useTranslations('settings')
  const { locale, setLocale } = useSettingsStore()

  return (
    <div>
      <SectionHeader title={t('language')} icon="🌍" />
      <div className="flex gap-3">
        {([['pl','🇵🇱 Polski'], ['en','🇬🇧 English']] as const).map(([lang, label]) => (
          <button
            key={lang}
            onClick={() => {
              setLocale(lang)
              setTimeout(() => window.location.reload(), 150)
            }}
            className="flex-1 py-3 rounded-xl border text-sm font-semibold transition-all"
            style={{
              background:  locale === lang ? 'rgba(59,130,246,0.15)' : '#1E293B',
              color:       locale === lang ? '#3B82F6' : '#64748B',
              borderColor: locale === lang ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
            }}
          >
            {label}
            {locale === lang && ' ✓'}
          </button>
        ))}
      </div>
    </div>
  )
}

function TelegramSection() {
  const t = useTranslations('settings')
  const [token,  setToken]  = useState('')
  const [chatId, setChatId] = useState('')
  const [saved,  setSaved]  = useState(false)

  function handleSave() {
    // TODO: POST /api/v1/settings/telegram
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div>
      <SectionHeader title={t('telegram')} icon="📨" desc="Alerty push gdy score przekroczy próg z watchlisty" />
      <div className="grid grid-cols-2 gap-3 mb-3">
        <Input
          label="Bot Token"
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="123456789:AAHxxxx..."
          hint="Utwórz bota przez @BotFather na Telegramie"
        />
        <Input
          label="Chat ID"
          value={chatId}
          onChange={e => setChatId(e.target.value)}
          placeholder="-100123456789"
          hint="Twój ID lub ID grupy (użyj @userinfobot)"
        />
      </div>
      <div className="flex items-center gap-3">
        <Button onClick={handleSave} size="sm" variant={saved ? 'ghost' : 'primary'}>
          {saved ? '✓ Zapisano' : t('save', { ns: 'common' }) ?? 'Zapisz'}
        </Button>
        <a
          href="https://t.me/BotFather"
          target="_blank"
          rel="noreferrer"
          className="text-xs text-brand-teal hover:underline"
        >
          Utwórz bota na Telegramie →
        </a>
      </div>
    </div>
  )
}

function AccountSection() {
  const t      = useTranslations('auth')
  const router = useRouter()
  const { userId, logout } = useAuthStore()

  function handleLogout() {
    logout()
    router.replace('/login')
  }

  return (
    <div>
      <SectionHeader title="Konto" icon="👤" />
      <div className="flex items-center justify-between py-3 border-b border-border">
        <div>
          <div className="text-sm font-semibold text-white">{userId}</div>
          <div className="text-xs text-muted">Zalogowany użytkownik</div>
        </div>
        <Button onClick={handleLogout} variant="danger" size="sm">
          {t('logout')}
        </Button>
      </div>
      <p className="text-xs text-muted mt-3">
        Usunięcie konta na etapie beta jest niedostępne. Skontaktuj się z nami jeśli chcesz
        usunąć swoje dane.
      </p>
    </div>
  )
}

function DiagnosticsSection() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function checkHealth() {
    setLoading(true)
    try {
      const resp = await fetch((process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/health')
      const data = await resp.json()
      setStatus(data)
    } catch {
      setStatus({ status: 'error', detail: 'Nie można połączyć się z API' })
    } finally {
      setLoading(false) }
  }

  return (
    <div>
      <SectionHeader title="Diagnostyka" icon="🔧" />
      <div className="flex items-center gap-3 mb-3">
        <Button onClick={checkHealth} loading={loading} variant="secondary" size="sm">
          Sprawdź status API
        </Button>
        <span className="text-xs text-muted">
          {process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}
        </span>
      </div>
      {status && (
        <div className="bg-surface-hi rounded-lg p-3 text-sm font-mono">
          <div className="flex items-center gap-2 mb-2">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: status.status === 'ok' ? '#22C55E' : '#EF4444' }}
            />
            <span className="text-white font-semibold">
              {status.status === 'ok' ? 'API działa poprawnie' : 'Błąd API'}
            </span>
          </div>
          {status.version && <div className="text-muted text-xs">Wersja: {status.version}</div>}
          {status.db      && <div className="text-muted text-xs">Baza: {status.db}</div>}
          {status.sources && (
            <div className="mt-2 space-y-0.5">
              {Object.entries(status.sources).map(([k, v]) => (
                <div key={k} className="text-xs flex gap-2">
                  <span className="text-muted w-24">{k}:</span>
                  <span style={{ color: v === 'ok' ? '#22C55E' : '#F59E0B' }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SettingsContent() {
  const t = useTranslations('settings')

  const sections = [
    { id:'appearance', content:<ThemeToggle /> },
    { id:'language',   content:<LanguageSection /> },
    { id:'telegram',   content:<TelegramSection /> },
    { id:'account',    content:<AccountSection /> },
    { id:'diagnostics',content:<DiagnosticsSection /> },
  ]

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-6">{t('title')}</h1>
      <div className="max-w-2xl space-y-5">
        {sections.map(({ id, content }) => (
          <div
            key={id}
            className="bg-surface border border-border rounded-xl2 p-5"
          >
            {content}
          </div>
        ))}
      </div>
    </AppShell>
  )
}

export default function SettingsPage() {
  return <AuthGuard><SettingsContent /></AuthGuard>
}
