'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBadge } from '../../components/ui/ScoreBadge'
import {
  Card, CardHeader, SectionHeader, Button, Input,
  Spinner, EmptyState, Tag, ChangeIndicator,
} from '../../components/ui'
import { analysisApi, watchlistApi, type Interval, type AnalysisResult } from '../../lib/api'
import { useRecentStore, useAuthStore } from '../../store'

type TabId = 'chart' | 'signals' | 'details' | 'scenarios' | 'strategies' | 'pdf'

const INTERVALS: { value: Interval; label: string }[] = [
  { value: '1m',  label: '1m'  },
  { value: '5m',  label: '5m'  },
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h',  label: '1h'  },
  { value: '1d',  label: '1D'  },
]

// ── Ticker search ─────────────────────────────────────────────────────

function TickerSearch({ onSelect }: { onSelect: (ticker: string) => void }) {
  const t          = useTranslations('analysis')
  const [q, setQ]  = useState('')
  const [results,  setResults]  = useState<{ symbol: string; name: string }[]>([])
  const [loading,  setLoading]  = useState(false)
  const [open,     setOpen]     = useState(false)
  const ref        = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!q.trim() || q.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await analysisApi.search(q)
        setResults(data)
        setOpen(true)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 350)
    return () => clearTimeout(timer)
  }, [q])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && q.trim()) {
      onSelect(q.trim().toUpperCase())
      setQ('')
      setOpen(false)
    }
  }

  return (
    <div ref={ref} className="relative">
      <Input
        placeholder={t('searchPlaceholder')}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={handleKeyDown}
        hint={t('searchHint')}
        prefixEl={loading ? <Spinner size="sm" /> : '🔍'}
      />
      {open && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-border rounded-xl shadow-card z-50 overflow-hidden">
          {results.map(r => (
            <button
              key={r.symbol}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-hi text-left transition-colors"
              onClick={() => {
                onSelect(r.symbol)
                setQ('')
                setOpen(false)
              }}
            >
              <span className="font-semibold text-sm text-white w-20">{r.symbol}</span>
              <span className="text-sm text-muted truncate">{r.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Lightweight chart wrapper ─────────────────────────────────────────

function PriceChart({ ticker, interval }: { ticker: string; interval: Interval }) {
  const t          = useTranslations('analysis')
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef     = useRef<any>(null)

  const { data, isLoading, error } = useSWR(
    ticker ? `candles-${ticker}-${interval}` : null,
    () => analysisApi.candles(ticker, interval),
    { refreshInterval: interval === '1m' ? 15_000 : interval === '5m' ? 30_000 : 60_000 },
  )

  useEffect(() => {
    if (!containerRef.current || !data?.candles.length) return

    // Dynamic import Lightweight Charts (SSR-safe)
    import('lightweight-charts').then(({ createChart, ColorType, LineStyle }) => {
      if (!containerRef.current) return

      // Destroy previous chart
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }

      const chart = createChart(containerRef.current, {
        width:  containerRef.current.clientWidth,
        height: 280,
        layout: {
          background:    { type: ColorType.Solid, color: 'transparent' },
          textColor:     '#94A3B8',
          fontFamily:    'Inter, sans-serif',
          fontSize:      11,
        },
        grid: {
          vertLines:   { color: 'rgba(255,255,255,0.04)' },
          horzLines:   { color: 'rgba(255,255,255,0.04)' },
        },
        crosshair:  { mode: 1 },
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.07)' },
        timeScale: {
          borderColor:   'rgba(255,255,255,0.07)',
          timeVisible:   interval !== '1d',
          secondsVisible: false,
        },
      })

      // Candles or area depending on interval
      if (['1d', '1h'].includes(interval)) {
        const series = chart.addCandlestickSeries({
          upColor:         '#22C55E',
          downColor:       '#EF4444',
          borderUpColor:   '#22C55E',
          borderDownColor: '#EF4444',
          wickUpColor:     '#22C55E',
          wickDownColor:   '#EF4444',
        })
        series.setData(data.candles.map(c => ({
          time:  (new Date(c.timestamp).getTime() / 1000) as any,
          open:  c.open,
          high:  c.high,
          low:   c.low,
          close: c.close,
        })))
      } else {
        const series = chart.addAreaSeries({
          lineColor:       '#14B8A6',
          topColor:        'rgba(20,184,166,0.25)',
          bottomColor:     'rgba(20,184,166,0.01)',
          lineWidth:       2,
        })
        series.setData(data.candles.map(c => ({
          time:  (new Date(c.timestamp).getTime() / 1000) as any,
          value: c.close,
        })))
      }

      chart.timeScale().fitContent()
      chartRef.current = chart

      // Responsive resize
      const resizeObs = new ResizeObserver(() => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
        }
      })
      if (containerRef.current) resizeObs.observe(containerRef.current)
      return () => resizeObs.disconnect()
    })

    return () => {
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [data, interval])

  if (isLoading) {
    return (
      <div className="h-[280px] flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="h-[280px] flex items-center justify-center text-sm text-muted">
        Nie udało się pobrać danych wykresu
      </div>
    )
  }

  return (
    <div>
      <div ref={containerRef} className="w-full" />
      <div className="flex items-center gap-3 mt-2 px-1">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-0.5 bg-brand-teal rounded" />
          <span className="text-xs text-muted">{t(`source.${data.source === 'Binance' ? 'binance' : 'yahoo'}`)}</span>
        </div>
        <span className="text-xs text-muted">·</span>
        <span className="text-xs text-muted">{data.candles.length} świec</span>
      </div>
    </div>
  )
}

// ── Score components table ────────────────────────────────────────────

function ComponentsTable({ analysis }: { analysis: AnalysisResult }) {
  const t = useTranslations('score')
  return (
    <div>
      <div className="text-sm font-semibold text-white mb-3">{t('components')}</div>
      <div className="grid grid-cols-2 gap-2">
        {analysis.components.map(comp => (
          <div key={comp.key} className="bg-surface-hi rounded-lg p-3">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs font-medium text-white">{comp.key}</span>
              <div className="flex items-center gap-2">
                <Tag>{(comp.weight * 100).toFixed(0)}%</Tag>
                <span
                  className="text-xs font-bold tabular-nums"
                  style={{ color: comp.score >= 60 ? '#22C55E' : comp.score >= 40 ? '#F59E0B' : '#EF4444' }}
                >
                  {Math.round(comp.score)}
                </span>
              </div>
            </div>
            <div className="h-1.5 rounded-full bg-surface overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${comp.score}%`,
                  background: comp.score >= 60 ? '#22C55E' : comp.score >= 40 ? '#F59E0B' : '#EF4444',
                }}
              />
            </div>
            <div className="text-[10px] text-muted mt-1 leading-tight">{comp.note}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Analysis page ─────────────────────────────────────────────────────

function AnalysisContent() {
  const searchParams = useSearchParams()
  const router       = useRouter()
  const t            = useTranslations('analysis')
  const { isAuth }   = useAuthStore()
  const { addTicker } = useRecentStore()

  const initialTicker = searchParams.get('ticker') ?? ''
  const [ticker,   setTicker]   = useState(initialTicker)
  const [interval, setInterval] = useState<Interval>('1d')
  const [activeTab, setActiveTab] = useState<TabId>('chart')

  const { data: analysis, isLoading, error } = useSWR(
    ticker ? `analysis-${ticker}` : null,
    () => analysisApi.analyze(ticker),
    { revalidateOnFocus: false },
  )

  const { data: signals } = useSWR(
    ticker && activeTab === 'signals' ? `signals-${ticker}` : null,
    () => analysisApi.signals(ticker),
  )

  // Save to recent + update URL on ticker change
  useEffect(() => {
    if (!ticker) return
    addTicker(ticker)
    router.replace(`/analysis?ticker=${ticker}`, { scroll: false })
  }, [ticker])

  async function handleAddToWatchlist() {
    if (!isAuth) { router.push('/login'); return }
    try {
      await watchlistApi.add(ticker)
    } catch { /* user-facing toast would go here */ }
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: 'chart',     label: t('tabs.chart')     },
    { id: 'signals',   label: t('tabs.signals')   },
    { id: 'details',   label: t('tabs.details')   },
    { id: 'scenarios', label: t('tabs.scenarios') },
    { id: 'strategies',label: t('tabs.strategies')},
    { id: 'pdf',       label: t('tabs.pdf')       },
  ]

  return (
    <AppShell>
      {/* Search */}
      <div className="mb-5 max-w-lg">
        <TickerSearch onSelect={setTicker} />
      </div>

      {!ticker ? (
        <EmptyState
          icon="📈"
          title={t('title')}
          desc="Wpisz symbol spółki, ETF-u lub kryptowaluty w polu wyszukiwania powyżej."
        />
      ) : isLoading ? (
        <div className="flex items-center justify-center h-48">
          <Spinner size="lg" />
        </div>
      ) : error || !analysis ? (
        <EmptyState
          icon="⚠️"
          title="Nie znaleziono danych"
          desc={`Brak danych dla ${ticker}. Sprawdź czy symbol jest poprawny.`}
          action={<Button onClick={() => setTicker('')} variant="ghost">Szukaj ponownie</Button>}
        />
      ) : (
        <div className="flex gap-5">
          {/* Main area */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-baseline gap-3">
                  <h1 className="text-2xl font-bold tracking-tight">{analysis.name}</h1>
                  <span className="text-muted text-sm">{ticker}</span>
                  {analysis.sector && <Tag>{analysis.sector}</Tag>}
                </div>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-2xl font-bold tabular-nums">
                    {analysis.price.toFixed(2)} {analysis.currency}
                  </span>
                </div>
              </div>

              {/* Scores */}
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <ScoreBadge score={analysis.total_score} size="lg" showLabel />
                  <div className="text-[10px] text-muted uppercase tracking-widest mt-1">{t('tabs.chart')} DT</div>
                </div>
                {analysis.score_st != null && (
                  <div className="text-center">
                    <ScoreBadge score={analysis.score_st} size="md" />
                    <div className="text-[10px] text-muted uppercase tracking-widest mt-1">⚡ ST</div>
                  </div>
                )}
                <Button onClick={handleAddToWatchlist} variant="secondary" size="sm">
                  ★ Watchlist
                </Button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border mb-4">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px"
                  style={{
                    color:        activeTab === tab.id ? '#22C55E' : '#64748B',
                    borderColor:  activeTab === tab.id ? '#22C55E' : 'transparent',
                    fontWeight:   activeTab === tab.id ? 600 : 400,
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === 'chart' && (
              <div className="bg-surface border border-border rounded-xl2 p-4">
                {/* Interval selector */}
                <div className="flex items-center gap-2 mb-4">
                  {INTERVALS.map(iv => (
                    <button
                      key={iv.value}
                      onClick={() => setInterval(iv.value)}
                      className="px-3 py-1 rounded-md text-xs font-medium transition-all"
                      style={{
                        background:  interval === iv.value ? 'rgba(20,184,166,0.2)' : '#1E293B',
                        color:       interval === iv.value ? '#14B8A6' : '#64748B',
                        border:      interval === iv.value ? '1px solid rgba(20,184,166,0.4)' : '1px solid rgba(255,255,255,0.07)',
                      }}
                    >
                      {iv.label}
                    </button>
                  ))}
                </div>
                <PriceChart ticker={ticker} interval={interval} />
              </div>
            )}

            {activeTab === 'signals' && signals && (
              <div className="space-y-4">
                {/* ATR */}
                {signals.atr && (
                  <Card>
                    <SectionHeader title="ATR – zasięg ruchu i stop-loss" icon="📏" />
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: 'ATR (14d)', value: `${(signals.atr as any).atr?.toFixed(2)} ${analysis.currency}` },
                        { label: 'Stop ciasny (1×)', value: `${((analysis.price - (signals.atr as any).atr)).toFixed(2)}` },
                        { label: 'Stop szeroki (1.5×)', value: `${((analysis.price - 1.5 * (signals.atr as any).atr)).toFixed(2)}` },
                      ].map(m => (
                        <div key={m.label} className="bg-surface-hi rounded-lg p-3 text-center">
                          <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{m.label}</div>
                          <div className="text-lg font-bold tabular-nums text-white">{m.value}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Stochastic */}
                {signals.stochastic && (
                  <Card>
                    <SectionHeader title="Stochastik %K/%D" icon="🎯" />
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold tabular-nums" style={{
                          color: signals.stochastic.k < 20 ? '#22C55E' : signals.stochastic.k > 80 ? '#EF4444' : '#F59E0B'
                        }}>
                          {signals.stochastic.k?.toFixed(0)}
                        </div>
                        <div className="text-xs text-muted">%K</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xl font-bold tabular-nums text-white">
                          {signals.stochastic.d?.toFixed(0)}
                        </div>
                        <div className="text-xs text-muted">%D</div>
                      </div>
                      <div
                        className="px-3 py-1.5 rounded-lg text-sm font-semibold"
                        style={{
                          background: signals.stochastic.signal === 'wyprzedanie' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                          color:      signals.stochastic.signal === 'wyprzedanie' ? '#22C55E' : '#EF4444',
                        }}
                      >
                        {signals.stochastic.signal}
                      </div>
                    </div>
                  </Card>
                )}

                {/* S/R levels */}
                {signals.levels && (
                  <Card>
                    <SectionHeader title="Wsparcie i opór" icon="📐" />
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs font-medium mb-2" style={{ color: '#22C55E' }}>🟢 Wsparcie</div>
                        {signals.levels.support?.slice().reverse().map((lvl: number) => {
                          const dist = ((analysis.price - lvl) / analysis.price * 100)
                          return (
                            <div key={lvl} className="flex justify-between py-1.5 border-b border-border">
                              <span className="font-semibold tabular-nums text-sm">{lvl.toFixed(2)}</span>
                              <span className="text-xs text-muted">−{dist.toFixed(1)}%</span>
                            </div>
                          )
                        })}
                      </div>
                      <div>
                        <div className="text-xs font-medium mb-2" style={{ color: '#EF4444' }}>🔴 Opór</div>
                        {signals.levels.resistance?.map((lvl: number) => {
                          const dist = ((lvl - analysis.price) / analysis.price * 100)
                          return (
                            <div key={lvl} className="flex justify-between py-1.5 border-b border-border">
                              <span className="font-semibold tabular-nums text-sm">{lvl.toFixed(2)}</span>
                              <span className="text-xs text-muted">+{dist.toFixed(1)}%</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            )}

            {activeTab === 'details' && (
              <ComponentsTable analysis={analysis} />
            )}

            {['scenarios', 'strategies'].includes(activeTab) && (
              <div className="h-48 flex items-center justify-center text-muted text-sm">
                Sekcja w trakcie implementacji
              </div>
            )}

            {activeTab === 'pdf' && (
              <div className="flex flex-col items-center justify-center py-16 gap-4">
                <div className="text-5xl">📄</div>
                <div className="font-semibold text-white">Raport PDF</div>
                <div className="text-sm text-muted max-w-sm text-center">
                  Pobierz pełny raport analizy z wynikiem score, składowymi
                  wskaźnikami i ostrzeżeniami.
                </div>
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/pdf/${ticker}`}
                  target="_blank"
                  rel="noreferrer"
                  download
                >
                  <button className="btn-primary px-6 py-3 text-sm font-semibold">
                    ⬇ Pobierz PDF — {ticker}
                  </button>
                </a>
                <p className="text-xs text-muted">
                  Plik zostanie pobrany bezpośrednio z serwera API.
                </p>
              </div>
            )}
          </div>

          {/* Right panel */}
          <div className="w-52 shrink-0 flex flex-col gap-3">
            {/* Key data */}
            <Card>
              <div className="text-[10px] text-muted uppercase tracking-widest mb-3">
                Kluczowe dane
              </div>
              {[
                { label: 'Beta',      value: (analysis.beta_info as any)?.beta?.toFixed(2) ?? '—' },
                { label: 'VWAP',      value: analysis.vwap ? `${(analysis.vwap as any).vwap?.toFixed(2)}` : '—' },
                { label: 'Sektor',    value: analysis.sector ?? '—' },
                { label: 'Branża',    value: analysis.industry?.substring(0, 18) ?? '—' },
              ].map(row => (
                <div key={row.label} className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-xs text-muted">{row.label}</span>
                  <span className="text-xs font-semibold text-white tabular-nums">{row.value}</span>
                </div>
              ))}
            </Card>

            {/* Red flags */}
            {analysis.red_flags.length > 0 && (
              <Card>
                <div className="text-[10px] text-muted uppercase tracking-widest mb-2">
                  Red flags
                </div>
                {analysis.red_flags.map((flag, i) => (
                  <div
                    key={i}
                    className="text-xs rounded-lg px-2.5 py-2 mb-1.5"
                    style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}
                  >
                    ⚠ {flag}
                  </div>
                ))}
              </Card>
            )}

            {/* MA crossover */}
            {analysis.ma_crossover && (
              <Card>
                <div className="text-[10px] text-muted uppercase tracking-widest mb-2">Trend MA</div>
                <div
                  className="text-xs rounded-lg px-2.5 py-2"
                  style={{
                    background: (analysis.ma_crossover as any).above ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    color:      (analysis.ma_crossover as any).above ? '#22C55E' : '#EF4444',
                  }}
                >
                  {(analysis.ma_crossover as any).above
                    ? '✓ MA50 > MA200 (układ byczy)'
                    : '✗ MA50 < MA200 (układ niedźwiedzi)'
                  }
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen"><Spinner size="lg" /></div>}>
      <AnalysisContent />
    </Suspense>
  )
}
