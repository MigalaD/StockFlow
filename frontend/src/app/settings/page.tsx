'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '../../components/layout/AppShell'
import { SectionHeader, Button, Input } from '../../components/ui'
import { useAuthStore, useSettingsStore } from '../../store'
import { AuthGuard } from '../../components/shared/AuthGuard'
import toast from 'react-hot-toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiCall(path: string, method = 'GET', body?: object) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('sf_token') : null
  const resp  = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
  return resp.json()
}

// ── Theme ─────────────────────────────────────────────────────────────

function ThemeSection() {
  const { theme, setTheme } = useSettingsStore()
  return (
    <div>
      <SectionHeader title="Motyw" icon="🎨" />
      <div className="flex gap-3">
        {([['dark','🌙 Ciemny'],['light','☀️ Jasny']] as const).map(([mode, label]) => (
          <button key={mode} onClick={() => { setTheme(mode); toast.success(`Motyw: ${label}`) }}
            className="flex-1 py-3 rounded-xl border text-sm font-semibold transition-all"
            style={{
              background:  theme === mode ? 'rgba(34,197,94,0.15)' : '#1E293B',
              color:       theme === mode ? '#22C55E' : '#64748B',
              borderColor: theme === mode ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.07)',
            }}>
            {label}{theme === mode && ' ✓'}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Language ──────────────────────────────────────────────────────────

function LanguageSection() {
  const { locale, setLocale } = useSettingsStore()
  return (
    <div>
      <SectionHeader title="Język / Language" icon="🌍" />
      <div className="flex gap-3">
        {([['pl','🇵🇱 Polski'],['en','🇬🇧 English']] as const).map(([lang, label]) => (
          <button key={lang} onClick={() => { setLocale(lang); setTimeout(() => window.location.reload(), 200) }}
            className="flex-1 py-3 rounded-xl border text-sm font-semibold transition-all"
            style={{
              background:  locale === lang ? 'rgba(59,130,246,0.15)' : '#1E293B',
              color:       locale === lang ? '#3B82F6' : '#64748B',
              borderColor: locale === lang ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
            }}>
            {label}{locale === lang && ' ✓'}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Telegram ──────────────────────────────────────────────────────────

function TelegramSection() {
  const [token,  setToken]  = useState('')
  const [chatId, setChatId] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  async function handleSave() {
    if (!token || !chatId) { toast.error('Wpisz token i chat ID'); return }
    setSaving(true)
    try {
      await apiCall('/api/v1/settings/telegram', 'POST', {
        telegram_token: token, telegram_chat_id: chatId
      })
      toast.success('Ustawienia Telegram zapisane')
    } catch {
      toast.error('Błąd zapisu — sprawdź czy serwer działa')
    } finally { setSaving(false) }
  }

  async function handleTest() {
    if (!token || !chatId) { toast.error('Najpierw wpisz dane'); return }
    setTesting(true)
    try {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text: '✅ StockFlow — test powiadomień działa!' }),
      })
      toast.success('Wiadomość testowa wysłana!')
    } catch { toast.error('Błąd wysyłania — sprawdź token i chat ID')
    } finally { setTesting(false) }
  }

  return (
    <div>
      <SectionHeader title="Alerty Telegram" icon="📨"
        desc="Powiadomienia gdy score przekroczy progi ustawione w watchliście" />
      <div className="grid grid-cols-2 gap-3 mb-3">
        <Input label="Bot Token" value={token} onChange={e => setToken(e.target.value)}
          placeholder="123456789:AAHxxxx..."
          hint="Utwórz przez @BotFather na Telegramie" />
        <Input label="Chat ID" value={chatId} onChange={e => setChatId(e.target.value)}
          placeholder="-100123456789"
          hint="Twój ID lub ID grupy (@userinfobot)" />
      </div>
      <div className="flex gap-2 items-center">
        <Button onClick={handleSave} loading={saving} size="sm">Zapisz</Button>
        <Button onClick={handleTest} loading={testing} variant="secondary" size="sm">Wyślij test</Button>
        <a href="https://t.me/BotFather" target="_blank" rel="noreferrer"
          className="text-xs text-brand-teal hover:underline">
          Utwórz bota →
        </a>
      </div>
    </div>
  )
}

// ── Account ────────────────────────────────────────────────────────────

function AccountSection() {
  const router = useRouter()
  const { userId, logout } = useAuthStore()

  function handleLogout() {
    logout()
    toast.success('Wylogowano pomyślnie')
    router.replace('/login')
  }

  return (
    <div>
      <SectionHeader title="Konto" icon="👤" />
      <div className="flex items-center justify-between py-3 border-b border-border mb-3">
        <div>
          <div className="text-sm font-semibold text-white">{userId}</div>
          <div className="text-xs text-muted">Zalogowany użytkownik</div>
        </div>
        <Button onClick={handleLogout} variant="danger" size="sm">Wyloguj</Button>
      </div>
      <p className="text-xs text-muted">
        Wersja beta — usunięcie konta dostępne na życzenie (napisz do nas przez GitHub Issues).
      </p>
    </div>
  )
}

// ── Diagnostics ────────────────────────────────────────────────────────

function DiagnosticsSection() {
  const [status,  setStatus]  = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function checkHealth() {
    setLoading(true)
    try {
      const data = await apiCall('/health')
      setStatus(data)
      toast.success('API działa poprawnie')
    } catch {
      setStatus({ status: 'error' })
      toast.error('Nie można połączyć się z API')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <SectionHeader title="Diagnostyka" icon="🔧" />
      <div className="flex items-center gap-3 mb-3">
        <Button onClick={checkHealth} loading={loading} variant="secondary" size="sm">
          Sprawdź status API
        </Button>
        <span className="text-xs text-muted font-mono">{API_URL}</span>
      </div>
      {status && (
        <div className="bg-surface-hi rounded-lg p-3 text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full"
              style={{ background: status.status === 'ok' ? '#22C55E' : '#EF4444' }} />
            <span className="font-semibold text-white">
              {status.status === 'ok' ? 'API działa poprawnie' : 'Problem z API'}
            </span>
          </div>
          {status.version && <div className="text-xs text-muted">Wersja: {status.version}</div>}
          {status.db      && (
            <div className="text-xs" style={{ color: status.db === 'ok' ? '#22C55E' : '#EF4444' }}>
              Baza: {status.db}
            </div>
          )}
          {status.sources && Object.entries(status.sources).map(([k, v]) => (
            <div key={k} className="text-xs flex gap-2">
              <span className="text-muted w-24">{k}:</span>
              <span style={{ color: v === 'ok' ? '#22C55E' : '#F59E0B' }}>{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Settings page ──────────────────────────────────────────────────────

function SettingsContent() {
  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">⚙️ Ustawienia</h1>
      <div className="max-w-2xl space-y-4">
        {[
          <ThemeSection    key="theme"    />,
          <LanguageSection key="lang"     />,
          <TelegramSection key="telegram" />,
          <AccountSection  key="account"  />,
          <DiagnosticsSection key="diag" />,
        ].map((section, i) => (
          <div key={i} className="bg-surface border border-border rounded-xl2 p-5">
            {section}
          </div>
        ))}
      </div>
    </AppShell>
  )
}

export default function SettingsPage() {
  return <AuthGuard><SettingsContent /></AuthGuard>
}
