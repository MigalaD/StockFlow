'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import { useAuthStore, useRecentStore } from '../store'
import { AppShell } from '../components/layout/AppShell'
import { ScoreBadge, ScoreBar, scoreColor } from '../components/ui/ScoreBadge'
import { Card, CardHeader, SectionHeader, EmptyState, Button, ChangeIndicator, Tag } from '../components/ui'
import { analysisApi, watchlistApi, scannerApi } from '../lib/api'
import type { WatchlistItem, ScanResultItem } from '../lib/api'
import Link from 'next/link'

// ── VIX Widget ────────────────────────────────────────────────────────

function VixWidget() {
  const t = useTranslations('dashboard.vix')
  const { data, isLoading } = useSWR(
    'vix',
    () => analysisApi.analyze('^VIX'),
    { refreshInterval: 300_000 }, // co 5 min
  )

  if (isLoading) {
    return (
      <div className="bg-surface border border-border rounded-xl2 p-4 animate-pulse h-[100px]" />
    )
  }

  const vix = data?.price ?? 18.4
  const color = vix < 15 ? '#22C55E' : vix < 25 ? '#F59E0B' : vix < 35 ? '#E07800' : '#EF4444'
  const label = vix < 15 ? t('calm') : vix < 25 ? t('normal') : vix < 35 ? t('elevated') : t('fear')

  return (
    <div
      className="rounded-xl2 p-4 border"
      style={{
        background:   color + '14',
        borderColor:  color + '40',
      }}
    >
      <div className="text-[10px] text-muted uppercase tracking-widest mb-2">{t('label')}</div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold tabular-nums" style={{ color }}>{vix.toFixed(1)}</span>
      </div>
      <div className="text-xs mt-1" style={{ color, opacity: 0.8 }}>{label}</div>
    </div>
  )
}

// ── Quick stat card ────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: {
  label: string; value: string; sub: string; color: string
}) {
  return (
    <div className="bg-surface border border-border rounded-xl2 p-4" style={{ borderTop: `3px solid ${color}` }}>
      <div className="text-[10px] uppercase tracking-widest text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</div>
      <div className="text-xs text-muted mt-1">{sub}</div>
    </div>
  )
}

// ── Watchlist row ─────────────────────────────────────────────────────

function WatchlistRow({ item, analysis }: {
  item:     WatchlistItem
  analysis: Awaited<ReturnType<typeof analysisApi.analyze>> | undefined
}) {
  const deltaScore = analysis && item.last_score != null
    ? analysis.total_score - item.last_score
    : null

  return (
    <tr className="border-b border-border hover:bg-surface-hi/40 transition-colors">
      <td className="px-4 py-3">
        <div className="font-semibold text-sm text-white">{item.ticker}</div>
        <div className="text-xs text-muted truncate max-w-[140px]">
          {analysis?.name ?? '—'}
        </div>
      </td>
      <td className="px-4 py-3 text-sm tabular-nums text-white">
        {analysis?.price != null
          ? `${analysis.price.toFixed(2)} ${analysis.currency}`
          : '—'
        }
      </td>
      <td className="px-4 py-3">
        {analysis
          ? <ScoreBar score={analysis.total_score} />
          : <span className="text-muted text-sm">—</span>
        }
      </td>
      <td className="px-4 py-3">
        {analysis?.score_st != null
          ? <ScoreBar score={analysis.score_st} />
          : <span className="text-muted text-sm">—</span>
        }
      </td>
      <td className="px-4 py-3">
        {deltaScore != null ? (
          <span
            className="text-sm font-semibold tabular-nums"
            style={{ color: deltaScore >= 0 ? '#22C55E' : '#EF4444' }}
          >
            {deltaScore >= 0 ? '+' : ''}{deltaScore.toFixed(1)}
          </span>
        ) : '—'}
      </td>
      <td className="px-4 py-3">
        <Link href={`/analysis?ticker=${item.ticker}`}>
          <Button variant="ghost" size="sm">Analizuj →</Button>
        </Link>
      </td>
    </tr>
  )
}

// ── Dashboard page ────────────────────────────────────────────────────

export default function DashboardPage() {
  const t      = useTranslations('dashboard')
  const { isAuth, userId } = useAuthStore()
  const { tickers: recentTickers } = useRecentStore()

  // Watchlist
  const { data: watchlist = [], isLoading: wlLoading } = useSWR(
    isAuth ? 'watchlist' : null,
    watchlistApi.get,
  )

  // Analiza każdej pozycji watchlisty
  const [analyses, setAnalyses] = useState<
    Record<string, Awaited<ReturnType<typeof analysisApi.analyze>>>
  >({})

  useEffect(() => {
    if (!watchlist.length) return
    const tickers = watchlist.slice(0, 8).map(w => w.ticker) // limit 8 dla dashboardu
    Promise.allSettled(tickers.map(t => analysisApi.analyze(t))).then(results => {
      const map: typeof analyses = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map[tickers[i]] = r.value
      })
      setAnalyses(map)
    })
  }, [watchlist])

  // Ostatni skan
  const { data: scan } = useSWR('scan-results', scannerApi.getResults, {
    refreshInterval: 0,
  })

  // Powitanie zależne od godziny
  const hour = new Date().getHours()
  const greeting =
    hour < 12 ? t('greeting.morning') :
    hour < 18 ? t('greeting.afternoon') :
                t('greeting.evening')

  const avgScore = watchlist.length > 0 && Object.values(analyses).length > 0
    ? (Object.values(analyses).reduce((s, a) => s + a.total_score, 0) /
       Object.values(analyses).length).toFixed(1)
    : null

  const topScan    = scan?.results.slice(0, 5) ?? []
  const bottomScan = scan?.results.slice(-5).reverse() ?? []

  return (
    <AppShell>
      {/* Greeting */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {greeting},{' '}
            <span style={{ color: '#22C55E' }}>{userId ?? 'Inwestorze'}</span> 👋
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

      {/* Top stats row */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <VixWidget />
        <StatCard
          label="Watchlista"
          value={String(watchlist.length)}
          sub="obserwowanych"
          color="#3B82F6"
        />
        <StatCard
          label="Avg Score DT"
          value={avgScore ?? '—'}
          sub="watchlista"
          color="#22C55E"
        />
        <StatCard
          label="Ostatni skan"
          value={String(scan?.total ?? 0)}
          sub="instrumentów"
          color="#14B8A6"
        />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-[1fr_280px] gap-4">

        {/* Watchlist table */}
        <div>
          <SectionHeader
            title={t('watchlist')}
            icon="★"
            action={
              <Link href="/watchlist">
                <Button variant="ghost" size="sm">Zarządzaj →</Button>
              </Link>
            }
          />

          {wlLoading ? (
            <div className="bg-surface border border-border rounded-xl2 animate-pulse h-48" />
          ) : watchlist.length === 0 ? (
            <div className="bg-surface border border-border rounded-xl2">
              <EmptyState
                icon="★"
                title={t('noWatchlist')}
                desc="Dodaj spółki na stronie Analiza lub Watchlista"
                action={
                  <Link href="/analysis">
                    <Button size="sm">Przejdź do Analizy</Button>
                  </Link>
                }
              />
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-xl2 overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr style={{ backgroundColor: '#0B1120' }}>
                    {['Instrument', 'Cena', 'Score DT', 'Score ST', 'Δ Score', ''].map(h => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-left text-[10px] uppercase tracking-widest text-muted font-medium border-b border-border"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {watchlist.map(item => (
                    <WatchlistRow
                      key={item.ticker}
                      item={item}
                      analysis={analyses[item.ticker]}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Recently viewed */}
          {recentTickers.length > 0 && (
            <div className="mt-5">
              <SectionHeader title="Ostatnio przeglądane" icon="🕐" />
              <div className="flex gap-2 flex-wrap">
                {recentTickers.map(ticker => (
                  <Link key={ticker} href={`/analysis?ticker=${ticker}`}>
                    <Tag className="cursor-pointer hover:border-brand-green hover:text-brand-green transition-colors">
                      {ticker}
                    </Tag>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: scan summary */}
        <div className="flex flex-col gap-4">
          {/* Top 5 */}
          <Card padding={false}>
            <CardHeader
              action={
                <Link href="/scanner">
                  <Button variant="ghost" size="sm">Skan →</Button>
                </Link>
              }
            >
              🟢 Top 5
            </CardHeader>
            <div className="py-2">
              {topScan.length === 0 ? (
                <div className="px-4 py-6 text-center text-sm text-muted">
                  {t('noScan')}
                </div>
              ) : topScan.map((r, i) => (
                <ScanMiniRow key={r.ticker} rank={i + 1} item={r} />
              ))}
            </div>
          </Card>

          {/* Bottom 5 */}
          {bottomScan.length > 0 && (
            <Card padding={false}>
              <CardHeader>🔴 Bottom 5</CardHeader>
              <div className="py-2">
                {bottomScan.map((r, i) => (
                  <ScanMiniRow key={r.ticker} rank={i + 1} item={r} />
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  )
}

function ScanMiniRow({ rank, item }: { rank: number; item: ScanResultItem }) {
  const color = scoreColor(item.score)
  return (
    <div className="flex items-center justify-between px-4 py-2 hover:bg-surface-hi/30">
      <div className="flex items-center gap-2.5">
        <span className="text-[10px] text-muted w-4 tabular-nums">{rank}</span>
        <Link href={`/analysis?ticker=${item.ticker}`}>
          <span className="text-sm font-semibold text-white hover:text-brand-green transition-colors">
            {item.ticker}
          </span>
        </Link>
      </div>
      <ScoreBar score={item.score} width="w-14" />
    </div>
  )
}
