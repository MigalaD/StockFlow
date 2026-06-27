'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { AppShell } from '../components/layout/AppShell'
import { ScoreBadge, scoreColor } from '../components/ui/ScoreBadge'
import { Card, SectionHeader, Button, Input, EmptyState, Spinner, ChangeIndicator } from '../components/ui'
import { watchlistApi } from '../lib/api'
import { useAuthStore } from '../store'
import { AuthGuard } from '../components/shared/AuthGuard'

function WatchlistCard({ item, onRemove }: {
  item: Awaited<ReturnType<typeof watchlistApi.get>>[number]
  onRemove: () => void
}) {
  const t    = useTranslations('watchlist')
  const [expanded, setExpanded] = useState(false)
  const [alertHigh, setAlertHigh] = useState(String(item.alert_high ?? 70))
  const [alertLow,  setAlertLow]  = useState(String(item.alert_low  ?? 30))
  const [saving,    setSaving]    = useState(false)

  const score = item.last_score
  const color = score != null ? scoreColor(score) : '#64748B'

  async function saveAlerts() {
    setSaving(true)
    try {
      await watchlistApi.setAlerts(item.ticker, {
        alert_high:      Number(alertHigh),
        alert_low:       Number(alertLow),
        alert_crossover: item.alert_crossover,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="bg-surface border border-border rounded-xl2 overflow-hidden"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {score != null && <ScoreBadge score={score} size="sm" />}
            <div>
              <div className="font-bold text-white">{item.ticker}</div>
              {item.added_at && (
                <div className="text-xs text-muted">
                  Dodano: {item.added_at.slice(0, 10)}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href={`/analysis?ticker=${item.ticker}`}>
              <Button variant="ghost" size="sm">Analizuj →</Button>
            </Link>
            <button
              onClick={() => setExpanded(e => !e)}
              className="text-muted hover:text-white text-sm px-2 py-1 rounded"
            >
              ⚙
            </button>
          </div>
        </div>
      </div>

      {/* Alerts expander */}
      {expanded && (
        <div className="border-t border-border p-4 bg-surface-hi/40">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <Input
              label={t('alertHigh')}
              type="number"
              value={alertHigh}
              onChange={e => setAlertHigh(e.target.value)}
              min={0} max={100}
            />
            <Input
              label={t('alertLow')}
              type="number"
              value={alertLow}
              onChange={e => setAlertLow(e.target.value)}
              min={0} max={100}
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={saveAlerts} loading={saving} size="sm">
              {t('saveAlerts')}
            </Button>
            <Button onClick={onRemove} variant="danger" size="sm">
              {t('remove')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function WatchlistContent() {
  const t                    = useTranslations('watchlist')
  const [newTicker, setNew]  = useState('')
  const [adding,    setAdding] = useState(false)
  const [addError,  setError]  = useState('')

  const { data: watchlist = [], isLoading, mutate } = useSWR(
    'watchlist',
    watchlistApi.get,
  )

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!newTicker.trim()) return
    setAdding(true)
    setError('')
    try {
      await watchlistApi.add(newTicker.trim().toUpperCase())
      setNew('')
      toast.success(`${newTicker.trim().toUpperCase()} dodano do watchlisty`)
      await mutate()
    } catch (err: any) {
      toast.error(err.detail ?? 'Błąd dodawania')
      setError(err.detail ?? 'Błąd')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove(ticker: string) {
    await watchlistApi.remove(ticker)
    toast.success(`${ticker} usunięto z watchlisty`)
    await mutate()
  }

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">{t('title')}</h1>

      {/* Add form */}
      <form onSubmit={handleAdd} className="flex gap-2 mb-6 max-w-md">
        <Input
          placeholder="np. AAPL, CDR.WA, BTC-USD"
          value={newTicker}
          onChange={e => setNew(e.target.value.toUpperCase())}
          error={addError}
          hint="Dla GPW użyj sufiksu .WA"
          className="flex-1"
        />
        <Button type="submit" loading={adding} className="shrink-0">
          {t('add')}
        </Button>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : watchlist.length === 0 ? (
        <EmptyState
          icon="★"
          title={t('empty')}
          desc={t('emptyHint')}
          action={
            <Link href="/analysis">
              <Button>Przejdź do Analizy</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {watchlist.map(item => (
            <WatchlistCard
              key={item.ticker}
              item={item}
              onRemove={() => handleRemove(item.ticker)}
            />
          ))}
        </div>
      )}
    </AppShell>
  )
}

export default function WatchlistPage() {
  return (
    <AuthGuard>
      <WatchlistContent />
    </AuthGuard>
  )
}
