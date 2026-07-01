'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { Settings2, ArrowRight, Plus, Trash2, Check, X } from 'lucide-react'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBar, scoreColor } from '../../components/ui/ScoreBadge'
import { SectionHeader, Button, Input, EmptyState, Spinner, Price } from '../../components/ui'
import { watchlistApi, analysisApi, type AnalysisResult } from '../../lib/api'
import toast from 'react-hot-toast'
import { AuthGuard } from '../../components/shared/AuthGuard'

type WLItem = Awaited<ReturnType<typeof watchlistApi.get>>[number]

// ── Sparkline ──────────────────────────────────────────────────────────

function Sparkline({ ticker }: { ticker: string }) {
  const { data } = useSWR(`hist-${ticker}`, () => analysisApi.history(ticker, 30),
    { revalidateOnFocus: false })
  if (!data || data.length < 2) return <div className="w-16 h-7" />
  const color = scoreColor(data[data.length - 1]?.score ?? 50)
  return (
    <ResponsiveContainer width={64} height={28}>
      <LineChart data={data.slice(-20)}>
        <Line type="monotone" dataKey="score" stroke={color} strokeWidth={1.5} dot={false} />
        <Tooltip
          contentStyle={{ background:'#0F1623', border:'1px solid rgba(255,255,255,0.1)', borderRadius:6, fontSize:10, padding:'4px 8px' }}
          formatter={(v: number) => [`${Math.round(v)}`, 'Score']}
          labelFormatter={() => ''}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Alerts editor (rozwijalny wiersz) ──────────────────────────────────

function AlertsEditor({ item, onRemove, onClose }: {
  item: WLItem; onRemove: () => void; onClose: () => void
}) {
  const t = useTranslations('watchlist')
  const [high, setHigh] = useState(String(item.alert_high ?? 70))
  const [low,  setLow]  = useState(String(item.alert_low  ?? 30))
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      await watchlistApi.setAlerts(item.ticker, {
        alert_high: Number(high), alert_low: Number(low),
        alert_crossover: item.alert_crossover,
      })
      toast.success(`Alerty dla ${item.ticker} zapisane`)
      onClose()
    } catch { toast.error('Błąd zapisu alertów') }
    finally { setSaving(false) }
  }

  return (
    <tr style={{ background: 'rgba(11,17,32,0.5)' }}>
      <td colSpan={7} className="px-4 py-4 border-b border-border">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="text-2xs text-muted uppercase tracking-wider mb-2 w-full">
            Alerty Telegram dla {item.ticker}
          </div>
          <Input label="Próg górny (score ≥)" type="number" value={high}
            onChange={e => setHigh(e.target.value)} min={0} max={100} className="w-36" />
          <Input label="Próg dolny (score ≤)" type="number" value={low}
            onChange={e => setLow(e.target.value)} min={0} max={100} className="w-36" />
          <Button onClick={save} loading={saving} size="sm">Zapisz alerty</Button>
          <Button onClick={onRemove} variant="danger" size="sm">Usuń z listy</Button>
        </div>
      </td>
    </tr>
  )
}

// ── Watchlist row ──────────────────────────────────────────────────────

function WatchRow({ item, analysis, onRemove }: {
  item: WLItem; analysis?: AnalysisResult; onRemove: () => void
}) {
  const [editing, setEditing]   = useState(false)
  const [confirming, setConfirming] = useState(false)
  const score = analysis?.total_score ?? item.last_score
  const deltaScore = analysis && item.last_score != null
    ? analysis.total_score - item.last_score : null

  return (
    <>
      <tr className="border-b border-border hover:bg-surface-2 transition-colors group">
        <td className="px-4 py-3">
          <Link href={`/analysis?ticker=${item.ticker}`} className="block">
            <div className="font-bold text-text-hi group-hover:text-brand-green transition-colors">
              {item.ticker}
            </div>
            <div className="text-2xs text-muted truncate max-w-[160px]">
              {analysis?.name ?? '—'}
            </div>
          </Link>
        </td>
        <td className="px-4 py-3 text-right">
          {analysis
            ? <Price value={analysis.price} currency={analysis.currency} className="text-sm text-text-hi" />
            : <Spinner size="sm" />}
        </td>
        <td className="px-4 py-3 w-32">
          {score != null ? <ScoreBar score={score} /> : <span className="text-muted text-xs">—</span>}
        </td>
        <td className="px-4 py-3 w-24">
          {analysis?.score_st != null
            ? <ScoreBar score={analysis.score_st} width="w-12" />
            : <span className="text-muted text-xs">—</span>}
        </td>
        <td className="px-4 py-3 text-right">
          {deltaScore != null ? (
            <span className="text-sm font-bold font-mono tabular-nums"
              style={{ color: deltaScore >= 0 ? '#22C55E' : '#EF4444' }}>
              {deltaScore >= 0 ? '+' : ''}{deltaScore.toFixed(1)}
            </span>
          ) : <span className="text-muted text-xs">—</span>}
        </td>
        <td className="px-4 py-3"><Sparkline ticker={item.ticker} /></td>
        <td className="px-4 py-3">
          <div className="flex items-center justify-end gap-1">
            {confirming ? (
              <div className="flex items-center gap-1 animate-fade-in">
                <span className="text-2xs text-muted mr-1">Usunąć?</span>
                <button onClick={onRemove}
                  className="p-1.5 rounded-md text-red-400 hover:bg-red-500/15 transition-colors"
                  title="Potwierdź usunięcie">
                  <Check className="w-4 h-4" />
                </button>
                <button onClick={() => setConfirming(false)}
                  className="p-1.5 rounded-md text-muted hover:text-text-hi hover:bg-surface-3 transition-colors"
                  title="Anuluj">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <button onClick={() => setEditing(e => !e)}
                  className="p-1.5 rounded-md text-muted hover:text-text-hi hover:bg-surface-3 transition-colors"
                  title="Alerty">
                  <Settings2 className="w-4 h-4" />
                </button>
                <Link href={`/analysis?ticker=${item.ticker}`}
                  className="p-1.5 rounded-md text-muted hover:text-brand-green hover:bg-surface-3 transition-colors"
                  title="Analizuj">
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <button onClick={() => setConfirming(true)}
                  className="p-1.5 rounded-md text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  title="Usuń z watchlisty">
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </td>
      </tr>
      {editing && <AlertsEditor item={item} onRemove={onRemove} onClose={() => setEditing(false)} />}
    </>
  )
}

// ── Page ───────────────────────────────────────────────────────────────

function WatchlistContent() {
  const t = useTranslations('watchlist')
  const [newTicker, setNew] = useState('')
  const [adding, setAdding] = useState(false)

  const { data: watchlist = [], isLoading, mutate } = useSWR('watchlist', watchlistApi.get)
  const [analyses, setAnalyses] = useState<Record<string, AnalysisResult>>({})

  useEffect(() => {
    if (!watchlist.length) return
    const tickers = watchlist.map(w => w.ticker)
    Promise.allSettled(tickers.map(t => analysisApi.analyze(t))).then(results => {
      const map: Record<string, AnalysisResult> = {}
      results.forEach((r, i) => { if (r.status === 'fulfilled') map[tickers[i]] = r.value })
      setAnalyses(map)
    })
  }, [watchlist.map(w => w.ticker).join(',')])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!newTicker.trim()) return
    setAdding(true)
    try {
      await watchlistApi.add(newTicker.trim().toUpperCase())
      toast.success(`${newTicker.trim().toUpperCase()} dodano`)
      setNew('')
      await mutate()
    } catch (err: any) {
      toast.error(err.detail ?? 'Błąd dodawania')
    } finally { setAdding(false) }
  }

  async function handleRemove(ticker: string) {
    await watchlistApi.remove(ticker)
    toast.success(`${ticker} usunięto`)
    await mutate()
  }

  const avgScore = Object.values(analyses).length
    ? (Object.values(analyses).reduce((s, a) => s + a.total_score, 0) / Object.values(analyses).length).toFixed(0)
    : null

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold">★ Watchlista</h1>
          {watchlist.length > 0 && (
            <p className="text-sm text-muted mt-0.5">
              {watchlist.length} {watchlist.length === 1 ? 'instrument' : 'instrumentów'}
              {avgScore && <> · średni score <span className="font-mono font-semibold" style={{ color: scoreColor(+avgScore) }}>{avgScore}</span></>}
            </p>
          )}
        </div>
      </div>

      {/* Add form */}
      <form onSubmit={handleAdd} className="flex gap-2 mb-5 max-w-md">
        <Input
          placeholder="Dodaj instrument: AAPL, CDR.WA, BTC-USD…"
          value={newTicker}
          onChange={e => setNew(e.target.value.toUpperCase())}
          hint="Dla GPW użyj sufiksu .WA"
          className="flex-1"
        />
        <Button type="submit" loading={adding} icon={<Plus className="w-4 h-4" />} className="shrink-0 h-fit">
          Dodaj
        </Button>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : watchlist.length === 0 ? (
        <EmptyState icon="★" title="Watchlista jest pusta"
          desc="Dodaj instrumenty które chcesz obserwować — będziesz widzieć ich score, ceny i zmiany w jednym miejscu."
          action={<Link href="/analysis"><Button>Przejdź do Analizy</Button></Link>} />
      ) : (
        <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr style={{ background: '#0B1120' }}>
                {[
                  ['Instrument','left'],['Cena','right'],['Score DT','left'],
                  ['ST','left'],['Δ Score','right'],['30 dni','left'],['','right'],
                ].map(([h, align]) => (
                  <th key={h as string}
                    className="px-4 py-2.5 text-2xs uppercase tracking-widest text-muted font-semibold border-b border-border"
                    style={{ textAlign: align as 'left' | 'right' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {watchlist.map(item => (
                <WatchRow key={item.ticker} item={item}
                  analysis={analyses[item.ticker]}
                  onRemove={() => handleRemove(item.ticker)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  )
}

export default function WatchlistPage() {
  return <AuthGuard><WatchlistContent /></AuthGuard>
}
