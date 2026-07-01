'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import Link from 'next/link'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { useAuthStore, useRecentStore } from '../store'
import { AppShell } from '../components/layout/AppShell'
import { ScoreBar, scoreColor } from '../components/ui/ScoreBadge'
import { SectionHeader, EmptyState, Button, Tag, Spinner } from '../components/ui'
import { analysisApi, watchlistApi, scannerApi } from '../lib/api'
import type { WatchlistItem, ScanResultItem, AnalysisResult } from '../lib/api'

// ── VIX Widget ─────────────────────────────────────────────────────────

function VixWidget() {
  const { data, isLoading } = useSWR(
    'vix', () => analysisApi.analyze('^VIX'),
    { refreshInterval: 300_000 }
  )
  if (isLoading) return (
    <div className="rounded-xl2 p-4 border border-border bg-surface-1 animate-pulse h-[90px]" />
  )
  const vix = data?.price ?? 18.4
  const color = vix < 15 ? '#22C55E' : vix < 25 ? '#F59E0B' : vix < 35 ? '#E07800' : '#EF4444'
  const label = vix < 15 ? '😌 Spokój' : vix < 25 ? '😐 Normalna zmienność' : vix < 35 ? '😟 Niepewność' : '😱 Panika'
  return (
    <div className="rounded-xl2 p-4 border" style={{ background: color + '14', borderColor: color + '40' }}>
      <div className="text-[10px] text-muted uppercase tracking-widest mb-1">VIX – Indeks strachu</div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold tabular-nums" style={{ color }}>{vix.toFixed(1)}</span>
      </div>
      <div className="text-xs mt-1" style={{ color, opacity: 0.8 }}>{label}</div>
    </div>
  )
}

// ── Stat card ──────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4" style={{ borderTop: `3px solid ${color}` }}>
      <div className="text-[10px] uppercase tracking-widest text-muted mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</div>
      <div className="text-xs text-muted mt-1">{sub}</div>
    </div>
  )
}

// ── Mini sparkline ─────────────────────────────────────────────────────

function ScoreSparkline({ ticker }: { ticker: string }) {
  const { data } = useSWR(
    `history-${ticker}`,
    () => analysisApi.history(ticker, 30),
    { revalidateOnFocus: false }
  )
  if (!data || data.length < 2) return null
  const color = scoreColor(data[data.length - 1]?.score ?? 50)
  return (
    <ResponsiveContainer width={64} height={28}>
      <LineChart data={data.slice(-20)}>
        <Line type="monotone" dataKey="score" stroke={color} strokeWidth={1.5} dot={false} />
        <Tooltip
          contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 6, fontSize: 10 }}
          formatter={(v: number) => [`${Math.round(v)}/100`, 'Score']}
          labelFormatter={(l) => String(l).slice(5)}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Watchlist table row ────────────────────────────────────────────────

function WatchlistRow({ item, analysis }: {
  item:     WatchlistItem
  analysis: AnalysisResult | undefined
}) {
  const deltaScore = analysis && item.last_score != null
    ? analysis.total_score - item.last_score
    : null

  return (
    <tr className="border-b border-border hover:bg-surface-2/40 transition-colors">
      <td className="px-4 py-3">
        <Link href={`/analysis?ticker=${item.ticker}`}
          className="font-bold text-white hover:text-brand-green transition-colors">
          {item.ticker}
        </Link>
        <div className="text-xs text-muted truncate max-w-[140px]">{analysis?.name ?? '—'}</div>
      </td>
      <td className="px-4 py-3 text-sm tabular-nums text-white">
        {analysis ? `${analysis.price.toFixed(2)} ${analysis.currency}` : <Spinner size="sm" />}
      </td>
      <td className="px-4 py-3">
        {analysis ? <ScoreBar score={analysis.total_score} /> : '—'}
      </td>
      <td className="px-4 py-3">
        {analysis?.score_st != null ? <ScoreBar score={analysis.score_st} /> : <span className="text-muted text-xs">—</span>}
      </td>
      <td className="px-4 py-3">
        {deltaScore != null ? (
          <span className="text-sm font-semibold tabular-nums"
            style={{ color: deltaScore >= 0 ? '#22C55E' : '#EF4444' }}>
            {deltaScore >= 0 ? '+' : ''}{deltaScore.toFixed(1)}
          </span>
        ) : '—'}
      </td>
      <td className="px-4 py-3">
        <ScoreSparkline ticker={item.ticker} />
      </td>
      <td className="px-4 py-3">
        <Link href={`/analysis?ticker=${item.ticker}`}>
          <button className="text-xs text-muted hover:text-brand-green transition-colors">→</button>
        </Link>
      </td>
    </tr>
  )
}

// ── Scan mini row ──────────────────────────────────────────────────────

function ScanRow({ rank, item }: { rank: number; item: ScanResultItem }) {
  const color = scoreColor(item.score)
  return (
    <div className="flex items-center justify-between px-4 py-2.5 hover:bg-surface-2/30 transition-colors border-b border-border last:border-0">
      <div className="flex items-center gap-2.5">
        <span className="text-[10px] text-muted w-4 tabular-nums">{rank}</span>
        <Link href={`/analysis?ticker=${item.ticker}`}>
          <span className="text-sm font-bold text-white hover:text-brand-green transition-colors">
            {item.ticker}
          </span>
        </Link>
        {item.sector && <Tag className="hidden md:inline-flex text-[10px]">{item.sector}</Tag>}
      </div>
      <ScoreBar score={item.score} width="w-16" />
    </div>
  )
}

// ── Recently viewed ────────────────────────────────────────────────────

function RecentlyViewed() {
  const { tickers } = useRecentStore()
  if (!tickers.length) return null
  return (
    <div className="mb-4">
      <div className="text-[10px] text-muted uppercase tracking-widest mb-2">🕐 Ostatnio przeglądane</div>
      <div className="flex gap-2 flex-wrap">
        {tickers.map(ticker => (
          <Link key={ticker} href={`/analysis?ticker=${ticker}`}>
            <span className="text-xs px-3 py-1.5 rounded-full border border-border text-muted
              hover:border-brand-green hover:text-brand-green transition-colors cursor-pointer">
              {ticker}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

// ── Dashboard ──────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { isAuth, userId, _hasHydrated, sessionVerified } = useAuthStore()
  const { tickers: recentTickers } = useRecentStore()
  const router = useRouter()

  // Niezalogowanych gości przekieruj na landing page
  useEffect(() => {
    if (_hasHydrated && sessionVerified && !isAuth) router.replace('/welcome')
  }, [_hasHydrated, sessionVerified, isAuth, router])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Dzień dobry' : hour < 18 ? 'Witaj' : 'Dobry wieczór'

  const { data: watchlist = [], isLoading: wlLoading } = useSWR(
    isAuth ? 'watchlist' : null,
    watchlistApi.get,
  )

  const [analyses, setAnalyses] = useState<Record<string, AnalysisResult>>({})

  useEffect(() => {
    if (!watchlist.length) return
    const tickers = watchlist.slice(0, 8).map(w => w.ticker)
    Promise.allSettled(tickers.map(t => analysisApi.analyze(t))).then(results => {
      const map: Record<string, AnalysisResult> = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map[tickers[i]] = r.value
      })
      setAnalyses(map)
    })
  }, [watchlist.map(w => w.ticker).join(',')])

  const { data: scan } = useSWR('scan-results', scannerApi.getResults, { refreshInterval: 0 })

  const avgScore = Object.values(analyses).length > 0
    ? (Object.values(analyses).reduce((s, a) => s + a.total_score, 0) / Object.values(analyses).length).toFixed(1)
    : null

  const topScan    = scan?.results.slice(0, 5) ?? []
  const bottomScan = [...(scan?.results ?? [])].sort((a,b) => a.score - b.score).slice(0, 5)
  const biggestChanges = watchlist
    .filter(w => w.last_score != null && analyses[w.ticker])
    .map(w => ({ ticker: w.ticker, delta: analyses[w.ticker].total_score - (w.last_score ?? 0) }))
    .filter(x => Math.abs(x.delta) >= 2)
    .sort((a,b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 3)

  return (
    <AppShell>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {greeting},{' '}
            <span style={{ color: '#22C55E' }}>{isAuth ? userId : 'Inwestorze'}</span> 👋
          </h1>
          <div className="text-sm text-muted mt-1">
            {new Date().toLocaleDateString('pl-PL', {
              weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            })}
          </div>
        </div>
        {!isAuth && (
          <Link href="/login">
            <Button variant="secondary" size="sm">Zaloguj się</Button>
          </Link>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <VixWidget />
        <StatCard label="Watchlista" value={String(watchlist.length)} sub="obserwowanych" color="#3B82F6" />
        <StatCard label="Avg Score DT" value={avgScore ?? '—'} sub="watchlista" color="#22C55E" />
        <StatCard label="Ostatni skan" value={String(scan?.total ?? 0)} sub={scan?.scanned_at ? scan.scanned_at.slice(0,10) : 'brak skanu'} color="#14B8A6" />
      </div>

      {/* Alerts row — największe zmiany */}
      {biggestChanges.length > 0 && (
        <div className="bg-surface-1 border border-border rounded-xl2 p-4 mb-5">
          <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">🔔 Największe zmiany score od ostatniej wizyty</div>
          <div className="flex gap-3 flex-wrap">
            {biggestChanges.map(({ ticker, delta }) => {
              const color = delta > 0 ? '#22C55E' : '#EF4444'
              return (
                <Link key={ticker} href={`/analysis?ticker=${ticker}`}>
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer hover:opacity-80"
                    style={{ borderColor: color + '40', background: color + '0D' }}>
                    <span className="font-bold text-white text-sm">{ticker}</span>
                    <span className="font-bold text-sm" style={{ color }}>
                      {delta > 0 ? '+' : ''}{delta.toFixed(1)} pkt
                    </span>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* Recently viewed */}
      <RecentlyViewed />

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4">

        {/* Watchlist table */}
        <div>
          <SectionHeader title="Watchlista" icon="★"
            action={<Link href="/watchlist"><Button variant="ghost" size="sm">Zarządzaj →</Button></Link>} />

          {wlLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : !isAuth ? (
            <EmptyState icon="🔐" title="Zaloguj się"
              desc="Zaloguj się aby zobaczyć swoją watchlistę i analizy"
              action={<Link href="/login"><Button size="sm">Zaloguj się</Button></Link>} />
          ) : watchlist.length === 0 ? (
            <EmptyState icon="★" title="Watchlista jest pusta"
              desc="Dodaj spółki które chcesz obserwować"
              action={<Link href="/analysis"><Button size="sm">Przejdź do Analizy</Button></Link>} />
          ) : (
            <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr style={{ backgroundColor: '#0B1120' }}>
                    {['Instrument','Cena','Score DT','Score ST','Δ Score','30d',''].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] uppercase tracking-widest text-muted font-medium border-b border-border">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {watchlist.map(item => (
                    <WatchlistRow key={item.ticker} item={item} analysis={analyses[item.ticker]} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: scan results */}
        <div className="space-y-4">
          {/* Top 5 */}
          <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="font-semibold text-sm text-white">🟢 Top 5 skanu</span>
              <Link href="/scanner">
                <Button variant="ghost" size="sm">Skan →</Button>
              </Link>
            </div>
            {topScan.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-muted">
                Brak wyników — uruchom skan rynku
              </div>
            ) : topScan.map((r, i) => <ScanRow key={r.ticker} rank={i + 1} item={r} />)}
          </div>

          {/* Bottom 5 */}
          {bottomScan.length > 0 && (
            <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <span className="font-semibold text-sm text-white">🔴 Bottom 5 skanu</span>
              </div>
              {bottomScan.map((r, i) => <ScanRow key={r.ticker} rank={i + 1} item={r} />)}
            </div>
          )}

          {/* Quick links */}
          <div className="bg-surface-1 border border-border rounded-xl2 p-4">
            <div className="text-[10px] text-muted uppercase tracking-widest mb-3">Szybkie akcje</div>
            <div className="space-y-2">
              {[
                { href: '/analysis',  icon: '📈', label: 'Analizuj instrument'   },
                { href: '/scanner',   icon: '🔍', label: 'Uruchom skan rynku'    },
                { href: '/portfolio', icon: '💼', label: 'Sprawdź portfolio'      },
                { href: '/compare',   icon: '🔀', label: 'Porównaj instrumenty'  },
              ].map(({ href, icon, label }) => (
                <Link key={href} href={href}>
                  <div className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-surface-2 transition-colors cursor-pointer">
                    <span className="text-base">{icon}</span>
                    <span className="text-sm text-white">{label}</span>
                    <span className="ml-auto text-muted text-xs">→</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
