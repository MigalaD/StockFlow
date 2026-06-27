'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { Button, Input, EmptyState, Spinner, SectionHeader, Card } from '../../components/ui'
import { scoreColor } from '../../components/ui/ScoreBadge'
import { analysisApi } from '../../lib/api'

interface BacktestResult {
  ticker:      string
  period:      string
  threshold:   number
  trades:      number
  win_rate:    number
  total_return: number
  buy_hold:    number
  max_dd:      number
  sharpe:      number
  equity_curve: { date: string; equity: number; bnh: number }[]
  trades_list:  { entry: string; exit: string; ret: number; duration: number }[]
}

// Lokalny backtest uproszczony (score threshold strategy)
async function runBacktest(ticker: string, threshold: number, period: string): Promise<BacktestResult> {
  // Pobierz historię score i dane cenowe równolegle
  const days = period === '1y' ? 365 : period === '2y' ? 730 : 180
  const [history, candles] = await Promise.all([
    analysisApi.history(ticker, days),
    analysisApi.candles(ticker, '1d'),
  ])

  if (!history.length || !candles.candles.length) throw new Error('Brak danych')

  // Symulacja: kup gdy score > threshold, sprzedaj gdy score < threshold - 10
  const priceMap = Object.fromEntries(
    candles.candles.map(c => [c.timestamp.slice(0, 10), c.close])
  )

  let inPosition   = false
  let entryPrice   = 0
  let entryDate    = ''
  let equity       = 100
  const trades: BacktestResult['trades_list'] = []
  const equityCurve: BacktestResult['equity_curve'] = []
  const startPrice = candles.candles[0]?.close ?? 1
  let bnh          = 100

  history.forEach((point, i) => {
    const price = priceMap[point.date]
    if (!price) return

    bnh = (price / startPrice) * 100

    if (!inPosition && point.score >= threshold) {
      inPosition = true
      entryPrice = price
      entryDate  = point.date
    } else if (inPosition && point.score < threshold - 10) {
      const ret      = ((price - entryPrice) / entryPrice) * 100
      const duration = history.slice(
        history.findIndex(h => h.date === entryDate), i
      ).length
      equity *= (1 + ret / 100)
      trades.push({ entry: entryDate, exit: point.date, ret: Math.round(ret * 100) / 100, duration })
      inPosition = false
    }

    equityCurve.push({ date: point.date.slice(5), equity: Math.round(equity * 100) / 100, bnh: Math.round(bnh * 100) / 100 })
  })

  const wins     = trades.filter(t => t.ret > 0).length
  const winRate  = trades.length ? (wins / trades.length) * 100 : 0
  const maxDD    = Math.min(...equityCurve.map(e => e.equity - 100))
  const returns  = trades.map(t => t.ret / 100)
  const avgRet   = returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : 0
  const stdRet   = returns.length > 1
    ? Math.sqrt(returns.reduce((a, b) => a + (b - avgRet) ** 2, 0) / returns.length)
    : 1
  const sharpe   = stdRet > 0 ? (avgRet / stdRet) * Math.sqrt(252) : 0

  return {
    ticker,
    period,
    threshold,
    trades:       trades.length,
    win_rate:     Math.round(winRate * 10) / 10,
    total_return: Math.round((equity - 100) * 100) / 100,
    buy_hold:     Math.round((bnh - 100) * 100) / 100,
    max_dd:       Math.round(maxDD * 100) / 100,
    sharpe:       Math.round(sharpe * 100) / 100,
    equity_curve: equityCurve.filter((_, i) => i % 3 === 0), // decimate for perf
    trades_list:  trades,
  }
}

function MetricCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div className="bg-surface-hi rounded-xl p-4 text-center">
      <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color: color ?? '#F8FAFC' }}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-1">{sub}</div>}
    </div>
  )
}

export default function BacktestPage() {
  const [ticker,    setTicker]    = useState('AAPL')
  const [threshold, setThreshold] = useState('60')
  const [period,    setPeriod]    = useState('1y')
  const [result,    setResult]    = useState<BacktestResult | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')

  async function handleRun() {
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await runBacktest(ticker.trim().toUpperCase(), parseInt(threshold), period)
      setResult(r)
    } catch (err: any) {
      setError(err.message ?? 'Błąd backtesta')
    } finally {
      setLoading(false) }
  }

  const stratColor  = result ? (result.total_return >= 0 ? '#22C55E' : '#EF4444') : '#F8FAFC'
  const bnhColor    = result ? (result.buy_hold    >= 0 ? '#14B8A6' : '#EF4444') : '#F8FAFC'

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">🧪 Backtest strategii</h1>

      {/* Disclaimer */}
      <div
        className="mb-5 rounded-lg px-4 py-3 text-sm leading-relaxed"
        style={{ background: 'rgba(245,158,11,0.08)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.2)' }}
      >
        ⚠ <strong>Wyniki historyczne nie gwarantują przyszłych zysków.</strong> Backtest używa
        danych dziennych i prostego progu score — pomija prowizje, poślizg cenowy i podatki.
        Cel: edukacyjne poznanie zachowania wskaźników, nie system transakcyjny.
      </div>

      {/* Controls */}
      <div className="bg-surface border border-border rounded-xl2 p-4 mb-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Input
            label="Symbol"
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder="AAPL"
          />
          <div>
            <div className="text-xs font-medium text-muted uppercase tracking-wider mb-1">Próg wejścia (score ≥)</div>
            <div className="flex gap-1">
              {[50, 60, 70].map(v => (
                <button
                  key={v}
                  onClick={() => setThreshold(String(v))}
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-all border"
                  style={{
                    background:  threshold === String(v) ? 'rgba(34,197,94,0.2)' : '#1E293B',
                    color:       threshold === String(v) ? '#22C55E' : '#64748B',
                    borderColor: threshold === String(v) ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.07)',
                  }}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-muted uppercase tracking-wider mb-1">Okres historii</div>
            <div className="flex gap-1">
              {[['6mo','6M'],['1y','1R'],['2y','2L']].map(([v, l]) => (
                <button
                  key={v}
                  onClick={() => setPeriod(v)}
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-all border"
                  style={{
                    background:  period === v ? 'rgba(59,130,246,0.2)' : '#1E293B',
                    color:       period === v ? '#3B82F6' : '#64748B',
                    borderColor: period === v ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
                  }}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end">
            <Button onClick={handleRun} loading={loading} className="w-full">
              ▶ Uruchom backtest
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted">
          Strategia: kup gdy Score DT ≥ {threshold} · sprzedaj gdy Score DT {'<'} {parseInt(threshold) - 10}
        </p>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          ⚠ {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Spinner size="lg" />
            <div className="text-sm text-muted mt-3">Testuję strategię score dla {ticker}…</div>
          </div>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-5 animate-fade-in">
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <MetricCard
              label="Zwrot strategii"
              value={`${result.total_return >= 0 ? '+' : ''}${result.total_return}%`}
              color={stratColor}
            />
            <MetricCard
              label="Buy & Hold"
              value={`${result.buy_hold >= 0 ? '+' : ''}${result.buy_hold}%`}
              color={bnhColor}
            />
            <MetricCard
              label="Transakcji"
              value={String(result.trades)}
              sub={`Win rate: ${result.win_rate}%`}
              color={result.win_rate >= 50 ? '#22C55E' : '#EF4444'}
            />
            <MetricCard
              label="Max drawdown"
              value={`${result.max_dd}%`}
              color={result.max_dd > -10 ? '#22C55E' : result.max_dd > -20 ? '#F59E0B' : '#EF4444'}
            />
            <MetricCard
              label="Sharpe ratio"
              value={String(result.sharpe)}
              color={result.sharpe >= 1 ? '#22C55E' : result.sharpe >= 0 ? '#F59E0B' : '#EF4444'}
              sub={result.sharpe >= 1 ? 'Dobry' : result.sharpe >= 0 ? 'Przeciętny' : 'Słaby'}
            />
            <MetricCard
              label="vs Buy&Hold"
              value={`${(result.total_return - result.buy_hold) >= 0 ? '+' : ''}${(result.total_return - result.buy_hold).toFixed(2)}%`}
              color={(result.total_return - result.buy_hold) >= 0 ? '#22C55E' : '#EF4444'}
              sub="Alpha"
            />
          </div>

          {/* Equity curve */}
          <div className="bg-surface border border-border rounded-xl2 p-4">
            <SectionHeader title="Krzywa kapitału" icon="📈" desc="Strategia score vs. Kup i trzymaj" />
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={result.equity_curve}>
                <XAxis dataKey="date" tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} width={38}
                  tickFormatter={v => `${v}%`} />
                <Tooltip
                  formatter={(v: number, name: string) => [
                    `${v >= 100 ? '+' : ''}${(v - 100).toFixed(2)}%`,
                    name === 'equity' ? 'Strategia' : 'Buy & Hold',
                  ]}
                  contentStyle={{ background:'#111827', border:'1px solid rgba(255,255,255,0.07)', borderRadius:8 }}
                  labelStyle={{ color:'#F8FAFC' }}
                />
                <ReferenceLine y={100} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 2" />
                <Legend
                  formatter={(v) => (
                    <span style={{ color:'#94A3B8', fontSize:11 }}>
                      {v === 'equity' ? 'Strategia score' : 'Buy & Hold'}
                    </span>
                  )}
                />
                <Line type="monotone" dataKey="equity" stroke="#22C55E" strokeWidth={2} dot={false} name="equity" />
                <Line type="monotone" dataKey="bnh"    stroke="#14B8A6" strokeWidth={1.5} dot={false} name="bnh" strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Trades list */}
          {result.trades_list.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm font-semibold text-white mb-3 select-none">
                Lista transakcji ({result.trades_list.length})
              </summary>
              <div className="bg-surface border border-border rounded-xl2 overflow-hidden">
                <table className="w-full border-collapse">
                  <thead>
                    <tr style={{ backgroundColor:'#0B1120' }}>
                      {['#','Wejście','Wyjście','Zwrot','Czas (dni)'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades_list.map((trade, i) => (
                      <tr key={i} className="border-b border-border hover:bg-surface-hi/30">
                        <td className="px-4 py-2.5 text-xs text-muted tabular-nums">{i + 1}</td>
                        <td className="px-4 py-2.5 text-xs font-mono text-white">{trade.entry}</td>
                        <td className="px-4 py-2.5 text-xs font-mono text-white">{trade.exit}</td>
                        <td className="px-4 py-2.5">
                          <span
                            className="text-sm font-bold tabular-nums"
                            style={{ color: trade.ret >= 0 ? '#22C55E' : '#EF4444' }}
                          >
                            {trade.ret >= 0 ? '+' : ''}{trade.ret}%
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-xs text-muted tabular-nums">{trade.duration}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </div>
      )}

      {!result && !loading && (
        <EmptyState
          icon="🧪"
          title="Skonfiguruj i uruchom backtest"
          desc="Wybierz instrument, próg score i okres historii. Strategia: kupuj gdy score przekroczy próg, sprzedaj gdy spadnie poniżej progu − 10."
        />
      )}
    </AppShell>
  )
}
