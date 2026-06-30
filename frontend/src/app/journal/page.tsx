'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { AppShell } from '../../components/layout/AppShell'
import { Card, SectionHeader, Button, Input, EmptyState, Spinner, Tag } from '../../components/ui'
import { journalApi, type JournalEntry } from '../../lib/api'
import { AuthGuard } from '../../components/shared/AuthGuard'

const DECISIONS = ['Kupno', 'Sprzedaż', 'Obserwacja', 'Analiza', 'Ominięcie okazji'] as const
type Decision = typeof DECISIONS[number]

const DECISION_COLORS: Record<string, string> = {
  'Kupno':           '#22C55E',
  'Sprzedaż':        '#EF4444',
  'Obserwacja':      '#3B82F6',
  'Analiza':         '#14B8A6',
  'Ominięcie okazji': '#F59E0B',
}

// ── Add entry form ────────────────────────────────────────────────────

function AddEntryForm({ onAdded }: { onAdded: () => void }) {
  const today = new Date().toISOString().slice(0, 10)
  const [fields, setFields] = useState({
    entry_date: today,
    ticker:     '',
    decision:   'Obserwacja' as Decision,
    reason:     '',
    score:      '',
    price:      '',
  })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const set = (k: keyof typeof fields) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setFields(f => ({ ...f, [k]: k === 'ticker' ? e.target.value.toUpperCase() : e.target.value }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!fields.ticker || !fields.reason.trim()) {
      setError('Symbol i uzasadnienie są wymagane'); return
    }
    setLoading(true); setError('')
    try {
      await journalApi.add({
        entry_date: fields.entry_date,
        ticker:     fields.ticker.trim(),
        decision:   fields.decision,
        reason:     fields.reason.trim(),
        score:      fields.score ? parseFloat(fields.score) : undefined,
        price:      fields.price ? parseFloat(fields.price) : undefined,
      })
      setFields({ entry_date: today, ticker: '', decision: 'Obserwacja', reason: '', score: '', price: '' })
      onAdded()
    } catch (err: any) {
      setError(err.detail ?? 'Błąd zapisu')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-5 mb-5">
      <div className="font-semibold text-sm text-text-hi mb-4">✏️ Nowy wpis</div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <Input
            label="Data"
            type="date"
            value={fields.entry_date}
            onChange={set('entry_date')}
          />
          <Input
            label="Symbol"
            value={fields.ticker}
            onChange={set('ticker')}
            placeholder="AAPL"
            hint="Dla GPW dodaj .WA"
          />
          <div>
            <label className="block text-xs font-medium text-muted uppercase tracking-wider mb-1">
              Decyzja
            </label>
            <select
              value={fields.decision}
              onChange={set('decision') as any}
              className="input"
            >
              {DECISIONS.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Score"
              type="number"
              value={fields.score}
              onChange={set('score')}
              placeholder="72"
              min="0" max="100"
            />
            <Input
              label="Cena"
              type="number"
              value={fields.price}
              onChange={set('price')}
              placeholder="185.5"
              step="any"
            />
          </div>
        </div>

        <div className="mb-3">
          <label className="block text-xs font-medium text-muted uppercase tracking-wider mb-1">
            Uzasadnienie / notatka
          </label>
          <textarea
            value={fields.reason}
            onChange={set('reason') as any}
            placeholder="Dlaczego ta decyzja? Co widziałem w danych? Czego się nauczyłem?"
            rows={3}
            className="input resize-none"
            required
          />
        </div>

        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-3">
            {error}
          </div>
        )}
        <Button type="submit" loading={loading} size="sm">
          Zapisz wpis
        </Button>
      </form>
    </div>
  )
}

// ── Journal entry card ────────────────────────────────────────────────

function EntryCard({ entry, onDelete }: { entry: JournalEntry; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const color = DECISION_COLORS[entry.decision] ?? '#64748B'

  async function handleDelete() {
    setDeleting(true)
    try { await journalApi.delete(entry.id); onDelete() }
    finally { setDeleting(false) }
  }

  return (
    <div
      className="bg-surface-1 border border-border rounded-xl2 overflow-hidden"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-surface-2/30 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xs text-muted tabular-nums font-mono shrink-0">{entry.entry_date}</span>
          <Link
            href={`/analysis?ticker=${entry.ticker}`}
            onClick={e => e.stopPropagation()}
            className="font-bold text-text-hi hover:text-brand-green transition-colors shrink-0"
          >
            {entry.ticker}
          </Link>
          <Tag color={color}>
            {entry.decision}
          </Tag>
          {!expanded && (
            <span className="text-xs text-muted truncate hidden md:block">
              {entry.reason.slice(0, 80)}{entry.reason.length > 80 ? '…' : ''}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {entry.score != null && (
            <span className="text-sm font-bold tabular-nums font-mono" style={{
              color: entry.score >= 60 ? '#22C55E' : entry.score >= 40 ? '#F59E0B' : '#EF4444'
            }}>
              {Math.round(entry.score)}/100
            </span>
          )}
          {entry.price != null && (
            <span className="text-xs text-muted tabular-nums font-mono">{entry.price.toFixed(2)}</span>
          )}
          <span className="text-muted text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-border">
          <p className="text-sm text-muted leading-relaxed mt-3 mb-3 whitespace-pre-wrap">
            {entry.reason}
          </p>
          <div className="flex items-center justify-between">
            <div className="flex gap-4 text-xs text-muted">
              {entry.score != null && <span>Score: <strong className="text-text-hi">{Math.round(entry.score)}</strong></span>}
              {entry.price != null && <span>Cena: <strong className="text-text-hi tabular-nums">{entry.price.toFixed(2)}</strong></span>}
              {entry.created_at && <span>Zapisano: {entry.created_at.slice(0, 16).replace('T', ' ')}</span>}
            </div>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-xs text-muted hover:text-red-400 transition-colors disabled:opacity-50"
            >
              {deleting ? 'Usuwanie…' : 'Usuń wpis'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Journal stats ─────────────────────────────────────────────────────

function JournalStats({ entries }: { entries: JournalEntry[] }) {
  const counts = DECISIONS.reduce<Record<string, number>>((acc, d) => {
    acc[d] = entries.filter(e => e.decision === d).length
    return acc
  }, {})

  const avgScore = entries.filter(e => e.score != null).length
    ? entries.filter(e => e.score != null)
        .reduce((s, e) => s + (e.score ?? 0), 0) /
      entries.filter(e => e.score != null).length
    : null

  const tickers = [...new Set(entries.map(e => e.ticker))].length

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      {[
        { label: 'Wpisów',        value: entries.length,             color: '#F8FAFC' },
        { label: 'Obserwowanych', value: tickers,                    color: '#3B82F6' },
        { label: 'Kupno',         value: counts['Kupno'] ?? 0,       color: '#22C55E' },
        { label: 'Avg Score',     value: avgScore ? `${avgScore.toFixed(1)}` : '—', color: '#14B8A6' },
      ].map(s => (
        <div key={s.label} className="bg-surface-1 border border-border rounded-xl2 p-3 text-center">
          <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{s.label}</div>
          <div className="text-2xl font-bold tabular-nums font-mono" style={{ color: s.color }}>{s.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Journal page ──────────────────────────────────────────────────────

function JournalContent() {
  const [filterTicker,   setFilterTicker]   = useState('')
  const [filterDecision, setFilterDecision] = useState('')

  const { data: entries = [], isLoading, mutate } = useSWR(
    'journal',
    () => journalApi.get(),
  )

  // Client-side filtering
  const filtered = entries.filter(e => {
    const tickerOk   = !filterTicker   || e.ticker.includes(filterTicker.toUpperCase())
    const decisionOk = !filterDecision || e.decision === filterDecision
    return tickerOk && decisionOk
  })

  // Group by month
  const byMonth = filtered.reduce<Record<string, JournalEntry[]>>((acc, e) => {
    const month = e.entry_date.slice(0, 7) // YYYY-MM
    if (!acc[month]) acc[month] = []
    acc[month].push(e)
    return acc
  }, {})

  const months = Object.keys(byMonth).sort().reverse()

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">📓 Dziennik inwestycyjny</h1>

      <AddEntryForm onAdded={() => mutate()} />

      {/* Stats */}
      {entries.length > 0 && <JournalStats entries={entries} />}

      {/* Filters */}
      {entries.length > 0 && (
        <div className="flex gap-3 mb-4 flex-wrap">
          <Input
            placeholder="Filtruj po tickerze…"
            value={filterTicker}
            onChange={e => setFilterTicker(e.target.value)}
            className="w-44"
          />
          <select
            value={filterDecision}
            onChange={e => setFilterDecision(e.target.value)}
            className="input w-44"
          >
            <option value="">Wszystkie decyzje</option>
            {DECISIONS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          {(filterTicker || filterDecision) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setFilterTicker(''); setFilterDecision('') }}
            >
              ✕ Wyczyść filtry
            </Button>
          )}
          <span className="text-xs text-muted self-center">
            {filtered.length} z {entries.length} wpisów
          </span>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : entries.length === 0 ? (
        <EmptyState
          icon="📓"
          title="Dziennik jest pusty"
          desc="Zapisuj swoje decyzje inwestycyjne, obserwacje i wnioski. To najlepsza nauka — przeglądanie własnych przemyśleń po czasie."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="🔍"
          title="Brak wyników"
          desc="Zmień kryteria filtrowania"
          action={
            <Button variant="ghost" onClick={() => { setFilterTicker(''); setFilterDecision('') }}>
              Wyczyść filtry
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {months.map(month => {
            const [year, mon] = month.split('-')
            const label = new Date(parseInt(year), parseInt(mon) - 1).toLocaleDateString('pl-PL', {
              month: 'long', year: 'numeric'
            })
            return (
              <div key={month}>
                <div className="text-xs font-semibold text-muted uppercase tracking-widest mb-2 pl-1">
                  {label} · {byMonth[month].length} wpisów
                </div>
                <div className="space-y-2">
                  {byMonth[month].map(entry => (
                    <EntryCard
                      key={entry.id}
                      entry={entry}
                      onDelete={() => mutate()}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}

export default function JournalPage() {
  return <AuthGuard><JournalContent /></AuthGuard>
}
