'use client'

import { useState, useEffect, useRef, Suspense, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBadge, scoreColor } from '../../components/ui/ScoreBadge'
import {
  Card, SectionHeader, Button, Input,
  Spinner, EmptyState, Tag,
} from '../../components/ui'
import { analysisApi, watchlistApi, type Interval, type AnalysisResult } from '../../lib/api'
import { useRecentStore, useAuthStore } from '../../store'

type TabId = 'chart' | 'signals' | 'details' | 'scenarios' | 'strategies' | 'pdf'
type ChartMode = 'candles' | 'line' | 'area'

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
  const [q, setQ]             = useState('')
  const [results, setResults] = useState<{ symbol: string; name: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen]       = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!q.trim() || q.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await analysisApi.search(q)
        setResults(data)
        setOpen(true)
      } catch { setResults([]) }
      finally { setLoading(false) }
    }, 350)
    return () => clearTimeout(timer)
  }, [q])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <Input
        placeholder="Wpisz symbol lub nazwę (np. AAPL, Apple)"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && q.trim()) {
            onSelect(q.trim().toUpperCase())
            setQ('')
            setOpen(false)
          }
        }}
        hint="Wciśnij Enter aby szukać"
        prefixEl={loading ? <Spinner size="sm" /> : '🔍'}
      />
      {open && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-border rounded-xl shadow-card z-50 overflow-hidden">
          {results.map(r => (
            <button
              key={r.symbol}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-hi text-left transition-colors"
              onClick={() => { onSelect(r.symbol); setQ(''); setOpen(false) }}
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

// ── Price Chart z pełnymi funkcjami ───────────────────────────────────

function PriceChart({
  ticker,
  interval,
  mode,
}: {
  ticker:   string
  interval: Interval
  mode:     ChartMode
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef     = useRef<any>(null)
  const seriesRef    = useRef<any>(null)
  const liveRef      = useRef<NodeJS.Timeout>()

  const { data, isLoading } = useSWR(
    ticker ? `candles-${ticker}-${interval}` : null,
    () => analysisApi.candles(ticker, interval),
    {
      refreshInterval: interval === '1m' ? 10_000
                     : interval === '5m' ? 20_000
                     : 60_000,
    },
  )

  // Inicjalizacja wykresu
  useEffect(() => {
    if (!containerRef.current || !data?.candles.length) return

    import('lightweight-charts').then(({ createChart, ColorType, CrosshairMode }) => {
      if (!containerRef.current) return

      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = null
      }

      const chart = createChart(containerRef.current, {
        width:  containerRef.current.clientWidth,
        height: 320,
        layout: {
          background:  { type: ColorType.Solid, color: 'transparent' },
          textColor:   '#94A3B8',
          fontFamily:  'Inter, sans-serif',
          fontSize:    11,
        },
        grid: {
          vertLines: { color: 'rgba(255,255,255,0.04)' },
          horzLines: { color: 'rgba(255,255,255,0.04)' },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.07)' },
        timeScale: {
          borderColor:    'rgba(255,255,255,0.07)',
          timeVisible:    interval !== '1d',
          secondsVisible: false,
          // Zoom i pan włączone domyślnie przez Lightweight Charts
        },
        // Scroll i zoom — pełna kontrola użytkownika
        handleScroll:  true,
        handleScale:   true,
      })

      let series: any

      if (mode === 'candles') {
        series = chart.addCandlestickSeries({
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
      } else if (mode === 'line') {
        series = chart.addLineSeries({
          color:       '#14B8A6',
          lineWidth:   2,
          crosshairMarkerVisible: true,
          crosshairMarkerRadius:  4,
        })
        series.setData(data.candles.map(c => ({
          time:  (new Date(c.timestamp).getTime() / 1000) as any,
          value: c.close,
        })))
      } else {
        series = chart.addAreaSeries({
          lineColor:   '#14B8A6',
          topColor:    'rgba(20,184,166,0.3)',
          bottomColor: 'rgba(20,184,166,0.01)',
          lineWidth:   2,
        })
        series.setData(data.candles.map(c => ({
          time:  (new Date(c.timestamp).getTime() / 1000) as any,
          value: c.close,
        })))
      }

      chart.timeScale().fitContent()
      chartRef.current  = chart
      seriesRef.current = series

      // Responsive resize
      const obs = new ResizeObserver(() => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
        }
      })
      if (containerRef.current) obs.observe(containerRef.current)

      return () => obs.disconnect()
    })

    return () => {
      clearInterval(liveRef.current)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = null
      }
    }
  }, [data, mode, interval])

  if (isLoading) return (
    <div className="h-80 flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  )

  if (!data) return (
    <div className="h-80 flex items-center justify-center text-muted text-sm">
      Nie udało się pobrać danych wykresu
    </div>
  )

  return (
    <div>
      <div ref={containerRef} className="w-full" />
      <div className="flex items-center gap-4 mt-2 px-1 text-xs text-muted">
        <span>📡 {data.source}</span>
        <span>·</span>
        <span>{data.candles.length} świec</span>
        <span>·</span>
        <span>Scroll = zoom · Drag = pan</span>
      </div>
    </div>
  )
}

// ── Scenarios (Scenariusze cenowe) ────────────────────────────────────

function ScenariosTab({ analysis }: { analysis: AnalysisResult }) {
  const price = analysis.price
  const score = analysis.total_score

  // Oblicz scenariusze na podstawie ATR i score
  const atrEst = price * 0.02 // Szacunkowy ATR = 2% ceny
  const bullMult = score >= 60 ? 2.5 : score >= 40 ? 1.5 : 0.8
  const bearMult = score >= 60 ? 0.8 : score >= 40 ? 1.5 : 2.5

  const scenarios = [
    {
      name:  '🐂 Bycze (optymistyczne)',
      prob:  score >= 60 ? '60%' : score >= 40 ? '40%' : '25%',
      color: '#22C55E',
      target: (price * (1 + bullMult * 0.05)).toFixed(2),
      desc:  'Kontynuacja trendu wzrostowego, przebicie oporu',
      cond:  'Score utrzymuje się powyżej 60, wolumen rośnie',
    },
    {
      name:  '↔️ Neutralne (boczne)',
      prob:  '30%',
      color: '#F59E0B',
      target: `${(price * 0.97).toFixed(2)} – ${(price * 1.03).toFixed(2)}`,
      desc:  'Konsolidacja w wąskim zakresie',
      cond:  'Brak wyraźnych sygnałów, niska zmienność',
    },
    {
      name:  '🐻 Niedźwiedzie (pesymistyczne)',
      prob:  score >= 60 ? '10%' : score >= 40 ? '30%' : '45%',
      color: '#EF4444',
      target: (price * (1 - bearMult * 0.05)).toFixed(2),
      desc:  'Korekta lub odwrócenie trendu',
      cond:  'Score spada poniżej 40, zwiększony wolumen sprzedaży',
    },
  ]

  return (
    <div className="space-y-4">
      <div
        className="rounded-xl p-3 text-xs leading-relaxed"
        style={{ background: 'rgba(245,158,11,0.08)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.2)' }}
      >
        ⚠ Scenariusze są orientacyjne i NIE stanowią prognozy ani porady inwestycyjnej.
        Oparte na bieżącym score i szacunkowym ATR.
      </div>

      {scenarios.map(s => (
        <div
          key={s.name}
          className="rounded-xl2 p-4"
          style={{ background: s.color + '0D', border: `1px solid ${s.color}30` }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold text-white">{s.name}</div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted">Prawdopodobieństwo:</span>
              <span className="font-bold text-sm" style={{ color: s.color }}>{s.prob}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-muted mb-1">Cel cenowy</div>
              <div className="font-bold tabular-nums text-white">{s.target} {analysis.currency}</div>
            </div>
            <div>
              <div className="text-xs text-muted mb-1">Warunek</div>
              <div className="text-xs text-white">{s.cond}</div>
            </div>
          </div>
          <div className="mt-2 text-xs text-muted">{s.desc}</div>
        </div>
      ))}

      <div className="text-xs text-muted text-center pt-2">
        Cena bieżąca: <strong className="text-white tabular-nums">{price.toFixed(2)} {analysis.currency}</strong>
        · Score DT: <strong style={{ color: scoreColor(score) }}>{Math.round(score)}/100</strong>
      </div>
    </div>
  )
}

// ── Strategies tab ────────────────────────────────────────────────────

function StrategiesTab({ analysis }: { analysis: AnalysisResult }) {
  const score = analysis.total_score

  const strategies = [
    {
      style:  '📈 Trend Following',
      match:  score >= 65,
      desc:   'Kup gdy trend wzrostowy potwierdzony (MA50 > MA200, score > 65). Stop-loss poniżej MA50.',
      risk:   'Średnie',
      horizon: 'Miesiące',
    },
    {
      style:  '↩️ Mean Reversion',
      match:  score < 40,
      desc:   'Kup po przecenie gdy RSI < 30 i score < 40. Cel: powrót do średniej.',
      risk:   'Wysokie',
      horizon: 'Dni–tygodnie',
    },
    {
      style:  '⚡ Swing Trading',
      match:  analysis.score_st != null && (analysis.score_st ?? 0) >= 60,
      desc:   'Krótkoterminowy ruch na podstawie Score ST. Wejście przy sygnale ST > 60.',
      risk:   'Wysokie',
      horizon: 'Dni',
    },
    {
      style:  '🏦 Buy & Hold',
      match:  score >= 55,
      desc:   'Długoterminowa inwestycja dla instrumentów z solidnymi fundamentami i score > 55.',
      risk:   'Niskie–Średnie',
      horizon: 'Lata',
    },
    {
      style:  '🛡️ Defensywna',
      match:  score >= 40 && score < 60,
      desc:   'Małe pozycje, szeroki stop-loss. Poczekaj na wyraźniejszy sygnał (score > 65 lub < 35).',
      risk:   'Niskie',
      horizon: 'Obserwacja',
    },
  ]

  return (
    <div className="space-y-3">
      {strategies.map(s => (
        <div
          key={s.style}
          className="rounded-xl p-4 border"
          style={{
            background:  s.match ? 'rgba(34,197,94,0.06)' : 'rgba(255,255,255,0.02)',
            borderColor: s.match ? 'rgba(34,197,94,0.3)'  : 'rgba(255,255,255,0.07)',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-sm text-white">{s.style}</span>
            <div className="flex items-center gap-2">
              {s.match && (
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(34,197,94,0.2)', color: '#22C55E' }}
                >
                  ✓ Pasuje do sytuacji
                </span>
              )}
              <Tag>{s.horizon}</Tag>
              <Tag color={s.risk === 'Niskie' ? '#22C55E' : s.risk === 'Średnie' ? '#F59E0B' : '#EF4444'}>
                Ryzyko: {s.risk}
              </Tag>
            </div>
          </div>
          <p className="text-sm text-muted leading-relaxed">{s.desc}</p>
        </div>
      ))}
      <p className="text-xs text-muted text-center pt-2">
        ⚠ Dopasowanie strategii jest automatyczne i NIE stanowi porady inwestycyjnej.
      </p>
    </div>
  )
}

// ── Components table ──────────────────────────────────────────────────

function DetailsTab({ analysis }: { analysis: AnalysisResult }) {
  return (
    <div className="space-y-5">
      {/* DT Components */}
      <div>
        <SectionHeader title="Składowe wyniku DT" icon="🧮"
          desc="Jak każdy wskaźnik wpłynął na końcowy wynik długoterminowy" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {analysis.components.map(comp => (
            <div key={comp.key} className="bg-surface-hi rounded-xl p-3">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-medium text-white">{comp.key}</span>
                <div className="flex items-center gap-2">
                  <Tag>{(comp.weight * 100).toFixed(0)}%</Tag>
                  <span className="text-xs font-bold tabular-nums"
                    style={{ color: scoreColor(comp.score) }}>
                    {Math.round(comp.score)}
                  </span>
                </div>
              </div>
              <div className="h-1.5 rounded-full bg-surface overflow-hidden mb-1">
                <div className="h-full rounded-full"
                  style={{ width: `${comp.score}%`, background: scoreColor(comp.score) }} />
              </div>
              <div className="text-[10px] text-muted leading-tight">{comp.note}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ST Components */}
      {analysis.components_st.length > 0 && (
        <div>
          <SectionHeader title="Składowe wyniku ST" icon="⚡"
            desc="Wskaźniki krótkoterminowe (swing trading)" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {analysis.components_st.map(comp => (
              <div key={comp.key} className="bg-surface-hi rounded-xl p-3">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-xs font-medium text-white">{comp.key}</span>
                  <span className="text-xs font-bold tabular-nums"
                    style={{ color: scoreColor(comp.score) }}>
                    {Math.round(comp.score)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-surface overflow-hidden mb-1">
                  <div className="h-full rounded-full"
                    style={{ width: `${comp.score}%`, background: scoreColor(comp.score) }} />
                </div>
                <div className="text-[10px] text-muted leading-tight">{comp.note}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Red flags */}
      {analysis.red_flags.length > 0 && (
        <div>
          <SectionHeader title="Red Flags" icon="⚠️" />
          {analysis.red_flags.map((flag, i) => (
            <div key={i} className="mb-2 rounded-lg px-3 py-2.5 text-sm"
              style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.2)' }}>
              ⚠ {flag}
            </div>
          ))}
        </div>
      )}

      {/* MA Crossover */}
      {analysis.ma_crossover && (
        <div>
          <SectionHeader title="Crossover MA" icon="📐" />
          <div className="rounded-lg px-3 py-2.5 text-sm"
            style={{
              background: (analysis.ma_crossover as any).above ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
              color:      (analysis.ma_crossover as any).above ? '#22C55E' : '#EF4444',
              border:     `1px solid ${(analysis.ma_crossover as any).above ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}>
            {(analysis.ma_crossover as any).above
              ? '✓ MA50 > MA200 — układ byczy (Golden Cross)'
              : '✗ MA50 < MA200 — układ niedźwiedzi (Death Cross)'}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Signals tab ───────────────────────────────────────────────────────

function SignalsTab({ ticker, price, currency }: {
  ticker: string; price: number; currency: string
}) {
  const { data: signals, isLoading } = useSWR(
    `signals-${ticker}`,
    () => analysisApi.signals(ticker),
  )

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>
  if (!signals)  return <div className="text-muted text-sm text-center py-8">Brak danych sygnałów</div>

  const atr    = (signals.atr as any)
  const stoch  = signals.stochastic
  const levels = signals.levels

  return (
    <div className="space-y-4">
      {/* ATR */}
      {atr && (
        <Card>
          <SectionHeader title="ATR – zasięg ruchu i stop-loss" icon="📏"
            desc="Average True Range — miara dziennej zmienności" />
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'ATR (14d)', value: `${atr.atr?.toFixed(2)} ${currency}` },
              { label: 'Stop ciasny (1×)', value: `${(price - atr.atr).toFixed(2)}`, color: '#EF4444' },
              { label: 'Stop szeroki (1.5×)', value: `${(price - 1.5 * atr.atr).toFixed(2)}`, color: '#F59E0B' },
            ].map(m => (
              <div key={m.label} className="bg-surface-hi rounded-xl p-3 text-center">
                <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{m.label}</div>
                <div className="text-lg font-bold tabular-nums" style={{ color: m.color ?? '#F8FAFC' }}>{m.value}</div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted mt-2">
            💡 Stop-loss ciasniejszy niż 1× ATR bywa wybijany przez zwykły szum rynkowy.
          </p>
        </Card>
      )}

      {/* Stochastic */}
      {stoch && (
        <Card>
          <SectionHeader title="Stochastik %K/%D" icon="🎯"
            desc="Oscylator momentum — obszary wykupienia i wyprzedania" />
          <div className="flex items-center gap-6 mb-4">
            {[
              { label: '%K', value: stoch.k?.toFixed(1),
                color: stoch.k < 20 ? '#22C55E' : stoch.k > 80 ? '#EF4444' : '#F59E0B' },
              { label: '%D', value: stoch.d?.toFixed(1), color: '#14B8A6' },
            ].map(m => (
              <div key={m.label} className="text-center">
                <div className="text-3xl font-bold tabular-nums" style={{ color: m.color }}>{m.value}</div>
                <div className="text-xs text-muted">{m.label}</div>
              </div>
            ))}
            <div
              className="px-3 py-1.5 rounded-lg text-sm font-semibold ml-4"
              style={{
                background: stoch.signal === 'wyprzedanie' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                color:      stoch.signal === 'wyprzedanie' ? '#22C55E' : '#EF4444',
              }}
            >
              {stoch.signal}
            </div>
            {stoch.crossed && (
              <Tag color="#14B8A6">{stoch.crossed}</Tag>
            )}
          </div>
          <div className="text-xs text-muted">
            %K {'<'} 20 = wyprzedanie · %K {'>'} 80 = przegrzanie
          </div>
        </Card>
      )}

      {/* OBV */}
      {signals.obv?.divergence && (
        <Card>
          <SectionHeader title="OBV – On-Balance Volume" icon="📊"
            desc="Kumulowany wolumen w kierunku ceny" />
          <div
            className="rounded-lg px-3 py-2.5 text-sm"
            style={{
              background: 'rgba(59,130,246,0.1)',
              color: '#3B82F6',
              border: '1px solid rgba(59,130,246,0.2)',
            }}
          >
            {(signals.obv.divergence as any).detected
              ? `⚠ Dywergencja OBV wykryta: ${(signals.obv.divergence as any).type}`
              : '✓ Brak dywergencji OBV — wolumen potwierdza ruch ceny'}
          </div>
        </Card>
      )}

      {/* S/R Levels */}
      {levels && (
        <Card>
          <SectionHeader title="Wsparcia i opory" icon="📐"
            desc="Historyczne poziomy zatrzymania ceny (ostatnie ~120 dni)" />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-medium mb-2" style={{ color: '#22C55E' }}>🟢 Wsparcie</div>
              {(levels.support ?? []).slice().reverse().slice(0, 4).map((lvl: number) => {
                const dist = ((price - lvl) / price * 100)
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
              {(levels.resistance ?? []).slice(0, 4).map((lvl: number) => {
                const dist = ((lvl - price) / price * 100)
                return (
                  <div key={lvl} className="flex justify-between py-1.5 border-b border-border">
                    <span className="font-semibold tabular-nums text-sm">{lvl.toFixed(2)}</span>
                    <span className="text-xs text-muted">+{dist.toFixed(1)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
          <p className="text-xs text-muted mt-2">
            ⚠ Poziomy historyczne — rynek nie musi ich respektować.
          </p>
        </Card>
      )}
    </div>
  )
}

// ── Main Analysis Page ────────────────────────────────────────────────

function AnalysisContent() {
  const searchParams  = useSearchParams()
  const router        = useRouter()
  const { isAuth }    = useAuthStore()
  const { addTicker } = useRecentStore()

  const initialTicker = searchParams.get('ticker') ?? ''
  const [ticker,    setTicker]    = useState(initialTicker)
  const [interval,  setInterval]  = useState<Interval>('1d')
  const [chartMode, setChartMode] = useState<ChartMode>('candles')
  const [activeTab, setActiveTab] = useState<TabId>('chart')

  const { data: analysis, isLoading, error } = useSWR(
    ticker ? `analysis-${ticker}` : null,
    () => analysisApi.analyze(ticker),
    { revalidateOnFocus: false },
  )

  useEffect(() => {
    if (!ticker) return
    addTicker(ticker)
    router.replace(`/analysis?ticker=${ticker}`, { scroll: false })
  }, [ticker])

  async function handleAddToWatchlist() {
    if (!isAuth) { router.push('/login'); return }
    try { await watchlistApi.add(ticker) } catch {}
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: 'chart',      label: '📈 Wykres'     },
    { id: 'signals',    label: '⚡ Sygnały ST'  },
    { id: 'details',    label: '📊 Analiza'     },
    { id: 'scenarios',  label: '🔮 Scenariusze' },
    { id: 'strategies', label: '🎯 Strategie'   },
    { id: 'pdf',        label: '📄 PDF'         },
  ]

  return (
    <AppShell>
      <div className="mb-5 max-w-lg">
        <TickerSearch onSelect={setTicker} />
      </div>

      {!ticker ? (
        <EmptyState
          icon="📈"
          title="Analiza instrumentu"
          desc="Wpisz symbol spółki, ETF-u lub kryptowaluty powyżej."
        />
      ) : isLoading ? (
        <div className="flex items-center justify-center h-48"><Spinner size="lg" /></div>
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
            {/* Sticky header */}
            <div
              className="sticky top-0 z-20 flex items-center justify-between py-3 mb-4 -mx-1 px-1"
              style={{
                background: 'linear-gradient(180deg, #0B1120 85%, rgba(11,17,32,0) 100%)',
              }}
            >
              <div>
                <div className="flex items-baseline gap-3">
                  <h1 className="text-xl font-bold tracking-tight">{analysis.name}</h1>
                  <span className="text-muted text-sm">{ticker}</span>
                  {analysis.sector && <Tag>{analysis.sector}</Tag>}
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-2xl font-bold tabular-nums">
                    {analysis.price.toFixed(2)} {analysis.currency}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <ScoreBadge score={analysis.total_score} size="lg" showLabel />
                  <div className="text-[10px] text-muted uppercase tracking-widest mt-1">DT</div>
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
            <div className="flex border-b border-border mb-4 overflow-x-auto">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="px-3 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px whitespace-nowrap"
                  style={{
                    color:       activeTab === tab.id ? '#22C55E' : '#64748B',
                    borderColor: activeTab === tab.id ? '#22C55E' : 'transparent',
                    fontWeight:  activeTab === tab.id ? 600 : 400,
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === 'chart' && (
              <div className="bg-surface border border-border rounded-xl2 p-4">
                {/* Controls row */}
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  {/* Intervals */}
                  <div className="flex gap-1">
                    {INTERVALS.map(iv => (
                      <button
                        key={iv.value}
                        onClick={() => setInterval(iv.value)}
                        className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                        style={{
                          background:  interval === iv.value ? 'rgba(20,184,166,0.2)' : '#1E293B',
                          color:       interval === iv.value ? '#14B8A6' : '#64748B',
                          border:      `1px solid ${interval === iv.value ? 'rgba(20,184,166,0.4)' : 'rgba(255,255,255,0.07)'}`,
                        }}
                      >
                        {iv.label}
                      </button>
                    ))}
                  </div>

                  <div className="w-px h-5 bg-border mx-1" />

                  {/* Chart mode */}
                  {(['candles','line','area'] as ChartMode[]).map(m => (
                    <button
                      key={m}
                      onClick={() => setChartMode(m)}
                      className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                      style={{
                        background:  chartMode === m ? 'rgba(34,197,94,0.2)' : '#1E293B',
                        color:       chartMode === m ? '#22C55E' : '#64748B',
                        border:      `1px solid ${chartMode === m ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.07)'}`,
                      }}
                    >
                      {m === 'candles' ? '🕯 Świece' : m === 'line' ? '📈 Linia' : '🌊 Obszar'}
                    </button>
                  ))}
                </div>

                <PriceChart ticker={ticker} interval={interval} mode={chartMode} />
              </div>
            )}

            {activeTab === 'signals'    && <SignalsTab   ticker={ticker} price={analysis.price} currency={analysis.currency} />}
            {activeTab === 'details'    && <DetailsTab   analysis={analysis} />}
            {activeTab === 'scenarios'  && <ScenariosTab analysis={analysis} />}
            {activeTab === 'strategies' && <StrategiesTab analysis={analysis} />}

            {activeTab === 'pdf' && (
              <div className="flex flex-col items-center justify-center py-16 gap-4">
                <div className="text-5xl">📄</div>
                <div className="font-semibold text-white">Raport PDF</div>
                <div className="text-sm text-muted max-w-sm text-center">
                  Pobierz pełny raport analizy z wynikiem score, składowymi i ostrzeżeniami.
                </div>
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/pdf/${ticker}`}
                  target="_blank"
                  rel="noreferrer"
                  download
                >
                  <Button>⬇ Pobierz PDF — {ticker}</Button>
                </a>
              </div>
            )}
          </div>

          {/* Right panel */}
          <div className="w-52 shrink-0 flex flex-col gap-3">
            <div className="bg-surface border border-border rounded-xl2 p-4">
              <div className="text-[10px] text-muted uppercase tracking-widest mb-3">Kluczowe dane</div>
              {[
                { label: 'Beta',     value: (analysis.beta_info as any)?.beta?.toFixed(2) ?? '—' },
                { label: 'VWAP',     value: analysis.vwap ? `${(analysis.vwap as any).vwap?.toFixed(2)}` : '—' },
                { label: 'Sektor',   value: analysis.sector ?? '—' },
                { label: 'Branża',   value: (analysis.industry ?? '—').substring(0, 18) },
                { label: 'Waluta',   value: analysis.currency },
                { label: 'Typ',      value: analysis.asset_type },
              ].map(row => (
                <div key={row.label} className="flex justify-between py-1.5 border-b border-border">
                  <span className="text-xs text-muted">{row.label}</span>
                  <span className="text-xs font-semibold text-white tabular-nums">{row.value}</span>
                </div>
              ))}
            </div>

            {analysis.red_flags.length > 0 && (
              <div className="bg-surface border border-border rounded-xl2 p-4">
                <div className="text-[10px] text-muted uppercase tracking-widest mb-2">Red Flags</div>
                {analysis.red_flags.slice(0, 3).map((flag, i) => (
                  <div key={i} className="text-xs rounded-lg px-2.5 py-2 mb-1.5"
                    style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}>
                    ⚠ {flag}
                  </div>
                ))}
              </div>
            )}

            {analysis.ma_crossover && (
              <div className="bg-surface border border-border rounded-xl2 p-4">
                <div className="text-[10px] text-muted uppercase tracking-widest mb-2">Trend MA</div>
                <div
                  className="text-xs rounded-lg px-2.5 py-2"
                  style={{
                    background: (analysis.ma_crossover as any).above ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    color:      (analysis.ma_crossover as any).above ? '#22C55E' : '#EF4444',
                  }}
                >
                  {(analysis.ma_crossover as any).above ? '✓ MA50 > MA200 (byczy)' : '✗ MA50 < MA200 (niedźwiedzi)'}
                </div>
              </div>
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
