'use client'

import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { Button, Input, EmptyState, Spinner, SectionHeader, Card, Tag } from '../../components/ui'
import { backtestApi, type BacktestResult, type GridResult, type WalkForwardResult } from '../../lib/api'

type View = 'single' | 'grid' | 'walkforward'

function MetricCard({ label, value, color, sub }: {
  label: string; value: string; color?: string; sub?: string
}) {
  return (
    <div className="bg-surface-2 rounded-xl p-4 text-center">
      <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color: color ?? '#F8FAFC' }}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-1">{sub}</div>}
    </div>
  )
}

// ── Single backtest ───────────────────────────────────────────────────

function SingleBacktest({ result }: { result: BacktestResult }) {
  const m = result.metrics
  const stratColor = m.total_return >= 0 ? '#22C55E' : '#EF4444'
  const bnhColor   = m.buyhold_return >= 0 ? '#14B8A6' : '#EF4444'
  const alpha      = m.total_return - m.buyhold_return

  return (
    <div className="space-y-5">
      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <MetricCard label="Zwrot strategii" value={`${m.total_return >= 0 ? '+' : ''}${m.total_return}%`} color={stratColor} />
        <MetricCard label="Buy & Hold" value={`${m.buyhold_return >= 0 ? '+' : ''}${m.buyhold_return}%`} color={bnhColor} />
        <MetricCard label="Alpha" value={`${alpha >= 0 ? '+' : ''}${alpha.toFixed(1)}%`}
          color={alpha >= 0 ? '#22C55E' : '#EF4444'} sub="vs B&H" />
        <MetricCard label="Transakcji" value={String(m.num_trades)} sub={`Win: ${m.win_rate}%`}
          color={m.win_rate >= 50 ? '#22C55E' : '#EF4444'} />
        <MetricCard label="Max DD" value={`${m.max_drawdown}%`}
          color={m.max_drawdown > -10 ? '#22C55E' : m.max_drawdown > -20 ? '#F59E0B' : '#EF4444'} />
        <MetricCard label="Sharpe" value={String(m.sharpe)}
          color={m.sharpe >= 1 ? '#22C55E' : m.sharpe >= 0 ? '#F59E0B' : '#EF4444'} />
        <MetricCard label="Sortino" value={String(m.sortino)}
          color={m.sortino >= 1 ? '#22C55E' : m.sortino >= 0 ? '#F59E0B' : '#EF4444'} />
      </div>

      {/* Equity curve */}
      <Card>
        <SectionHeader title="Krzywa kapitału" icon="📈" desc="Strategia score vs. Kup i trzymaj" />
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={result.equity_curve}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="date" tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} width={50}
              tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
            <Tooltip
              formatter={(v: number, name: string) => [
                `${v.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł`,
                name === 'strategy' ? 'Strategia' : 'Buy & Hold',
              ]}
              contentStyle={{ background:'#111827', border:'1px solid rgba(255,255,255,0.07)', borderRadius:8 }}
              labelStyle={{ color:'#F8FAFC' }}
            />
            <Legend formatter={(v) => (
              <span style={{ color:'#94A3B8', fontSize:11 }}>
                {v === 'strategy' ? 'Strategia score' : 'Buy & Hold'}
              </span>
            )} />
            <Line type="monotone" dataKey="strategy" stroke="#22C55E" strokeWidth={2} dot={false} name="strategy" />
            <Line type="monotone" dataKey="buyhold" stroke="#14B8A6" strokeWidth={1.5} dot={false} name="buyhold" strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Trades */}
      {result.trades.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-white mb-3 select-none">
            Lista transakcji ({result.trades.length})
          </summary>
          <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
            <table className="w-full border-collapse">
              <thead>
                <tr style={{ backgroundColor:'#0B1120' }}>
                  {['#','Wejście','Wyjście','Cena kup.','Cena sprz.','Zwrot'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i} className="border-b border-border hover:bg-surface-2/30">
                    <td className="px-4 py-2.5 text-xs text-muted tabular-nums">{i+1}</td>
                    <td className="px-4 py-2.5 text-xs font-mono text-white">{t.entry_date}</td>
                    <td className="px-4 py-2.5 text-xs font-mono text-white">
                      {t.exit_date}{t.still_open && <span className="text-amber-400 ml-1">(otwarta)</span>}
                    </td>
                    <td className="px-4 py-2.5 text-xs tabular-nums text-muted">{t.entry_price}</td>
                    <td className="px-4 py-2.5 text-xs tabular-nums text-muted">{t.exit_price}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-sm font-bold tabular-nums"
                        style={{ color: t.return_pct >= 0 ? '#22C55E' : '#EF4444' }}>
                        {t.return_pct >= 0 ? '+' : ''}{t.return_pct}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  )
}

// ── Grid heatmap ──────────────────────────────────────────────────────

function GridHeatmap({ grid }: { grid: GridResult }) {
  const buys  = [...new Set(grid.cells.map(c => c.buy))].sort((a,b) => a-b)
  const sells = [...new Set(grid.cells.map(c => c.sell))].sort((a,b) => b-a)
  const returns = grid.cells.map(c => c.return)
  const maxRet = Math.max(...returns)
  const minRet = Math.min(...returns)

  function cellColor(ret: number): string {
    if (ret >= 0) {
      const intensity = maxRet > 0 ? ret / maxRet : 0
      return `rgba(34,197,94,${0.15 + intensity * 0.6})`
    } else {
      const intensity = minRet < 0 ? ret / minRet : 0
      return `rgba(239,68,68,${0.15 + intensity * 0.6})`
    }
  }

  const getCell = (buy: number, sell: number) =>
    grid.cells.find(c => c.buy === buy && c.sell === sell)

  return (
    <div className="space-y-4">
      <div className="rounded-xl p-3 text-xs leading-relaxed"
        style={{ background:'rgba(245,158,11,0.08)', color:'#F59E0B', border:'1px solid rgba(245,158,11,0.2)' }}>
        ⚠ <strong>Uwaga na overfitting.</strong> Najlepsza kombinacja w przeszłości NIE gwarantuje
        wyników w przyszłości. Szukaj raczej "wysp" stabilnych dobrych wyników niż pojedynczego maksimum.
      </div>

      <Card>
        <SectionHeader title="Heatmapa progów (buy × sell)" icon="🔥"
          desc={`Najlepsza: buy ${grid.best.buy} / sell ${grid.best.sell} → ${grid.best.return >= 0 ? '+' : ''}${grid.best.return}% · Buy&Hold: ${grid.buyhold_return}%`} />
        <div className="overflow-x-auto">
          <table className="border-collapse mx-auto">
            <thead>
              <tr>
                <th className="text-[10px] text-muted p-1.5">sell\\buy</th>
                {buys.map(buy => (
                  <th key={buy} className="text-[10px] text-muted p-1.5 font-medium">{buy}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sells.map(sell => (
                <tr key={sell}>
                  <td className="text-[10px] text-muted p-1.5 font-medium text-right">{sell}</td>
                  {buys.map(buy => {
                    const cell = getCell(buy, sell)
                    const isBest = grid.best.buy === buy && grid.best.sell === sell
                    return (
                      <td key={buy} className="p-0.5">
                        {cell ? (
                          <div
                            className="w-12 h-9 flex items-center justify-center rounded text-[10px] font-bold tabular-nums relative"
                            style={{
                              background: cellColor(cell.return),
                              color: '#F8FAFC',
                              border: isBest ? '2px solid #22C55E' : '1px solid transparent',
                            }}
                            title={`buy ${buy} / sell ${sell}: ${cell.return}%`}
                          >
                            {cell.return}
                            {isBest && <span className="absolute -top-1 -right-1 text-[8px]">★</span>}
                          </div>
                        ) : (
                          <div className="w-12 h-9 bg-surface-2/30 rounded" />
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-center gap-4 mt-4 text-[10px] text-muted">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-3 rounded" style={{ background:'rgba(239,68,68,0.7)' }} />
            <span>Strata</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-3 rounded" style={{ background:'rgba(34,197,94,0.7)' }} />
            <span>Zysk</span>
          </div>
          <span>★ = najlepsza kombinacja</span>
        </div>
      </Card>
    </div>
  )
}

// ── Walk forward ──────────────────────────────────────────────────────

function WalkForward({ wf }: { wf: WalkForwardResult }) {
  const winRate = wf.summary.win_rate_pct
  return (
    <div className="space-y-4">
      <div className="rounded-xl p-3 text-xs leading-relaxed"
        style={{ background:'rgba(59,130,246,0.08)', color:'#93C5FD', border:'1px solid rgba(59,130,246,0.2)' }}>
        ℹ️ <strong>Test stabilności w czasie.</strong> Historia podzielona na {wf.summary.n_windows} okien.
        Jeśli strategia działa tylko w 1 oknie — to prawdopodobnie przypadek, nie reguła.
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Okien" value={String(wf.summary.n_windows)} />
        <MetricCard label="Wygranych vs B&H" value={String(wf.summary.wins)}
          color={wf.summary.wins > wf.summary.n_windows / 2 ? '#22C55E' : '#EF4444'} />
        <MetricCard label="Skuteczność" value={`${winRate}%`}
          color={winRate >= 60 ? '#22C55E' : winRate >= 40 ? '#F59E0B' : '#EF4444'}
          sub={winRate >= 60 ? 'Stabilna' : winRate >= 40 ? 'Niepewna' : 'Niestabilna'} />
      </div>

      {/* Windows table */}
      <Card>
        <SectionHeader title="Wyniki per okres" icon="📅" />
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr style={{ backgroundColor:'#0B1120' }}>
                {['Okres','Strategia','Buy&Hold','Lepsza?','Transakcji','Max DD'].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {wf.windows.map((w, i) => (
                <tr key={i} className="border-b border-border hover:bg-surface-2/30">
                  <td className="px-3 py-2.5 text-xs font-mono text-white">
                    {w.okres_od}<br/><span className="text-muted">→ {w.okres_do}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="text-sm font-bold tabular-nums"
                      style={{ color: w['strategia_%'] >= 0 ? '#22C55E' : '#EF4444' }}>
                      {w['strategia_%'] >= 0 ? '+' : ''}{w['strategia_%']}%
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-sm tabular-nums text-muted">
                    {w['kup_i_trzymaj_%'] >= 0 ? '+' : ''}{w['kup_i_trzymaj_%']}%
                  </td>
                  <td className="px-3 py-2.5">
                    {w.lepsza_niz_bh
                      ? <Tag color="#22C55E">✓ Tak</Tag>
                      : <Tag color="#EF4444">✗ Nie</Tag>}
                  </td>
                  <td className="px-3 py-2.5 text-xs tabular-nums text-muted">{w.liczba_transakcji}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums"
                    style={{ color: w['max_obsuniecie_%'] > -15 ? '#94A3B8' : '#EF4444' }}>
                    {w['max_obsuniecie_%']}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

// ── Backtest page ─────────────────────────────────────────────────────

export default function BacktestPage() {
  const [ticker, setTicker]   = useState('AAPL')
  const [buy, setBuy]         = useState('65')
  const [sell, setSell]       = useState('35')
  const [period, setPeriod]   = useState('2y')
  const [view, setView]       = useState<View>('single')

  const [single, setSingle]   = useState<BacktestResult | null>(null)
  const [grid, setGrid]       = useState<GridResult | null>(null)
  const [wf, setWf]           = useState<WalkForwardResult | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  async function run() {
    setLoading(true); setError('')
    setSingle(null); setGrid(null); setWf(null)
    const t = ticker.trim().toUpperCase()
    try {
      if (view === 'single') {
        setSingle(await backtestApi.run(t, { period, buy: +buy, sell: +sell }))
      } else if (view === 'grid') {
        setGrid(await backtestApi.grid(t, period))
      } else {
        setWf(await backtestApi.walkForward(t, { buy: +buy, sell: +sell }))
      }
    } catch (err: any) {
      setError(err.detail ?? 'Błąd backtestu')
    } finally { setLoading(false) }
  }

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">🧪 Backtest strategii</h1>

      {/* Disclaimer */}
      <div className="mb-5 rounded-lg px-4 py-3 text-sm leading-relaxed"
        style={{ background:'rgba(245,158,11,0.08)', color:'#F59E0B', border:'1px solid rgba(245,158,11,0.2)' }}>
        ⚠ <strong>Wyniki historyczne nie gwarantują przyszłych zysków.</strong> Backtest pomija
        prowizje, poślizg i podatki. Cel: edukacyjne poznanie zachowania score, nie system transakcyjny.
      </div>

      {/* View tabs */}
      <div className="flex gap-2 mb-4">
        {([
          ['single','📈 Pojedynczy test'],
          ['grid','🔥 Heatmapa progów'],
          ['walkforward','📅 Walk-forward'],
        ] as [View,string][]).map(([v, label]) => (
          <button key={v} onClick={() => { setView(v); setSingle(null); setGrid(null); setWf(null) }}
            className="px-3 py-2 rounded-lg text-sm font-medium transition-all border"
            style={{
              background:  view === v ? 'rgba(34,197,94,0.15)' : '#111827',
              color:       view === v ? '#22C55E' : '#64748B',
              borderColor: view === v ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.07)',
            }}>
            {label}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="bg-surface-1 border border-border rounded-xl2 p-4 mb-5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
          <Input label="Symbol" value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="AAPL" />
          {view !== 'grid' && (
            <>
              <Input label="Próg kupna (≥)" type="number" value={buy} onChange={e => setBuy(e.target.value)} min="0" max="100" />
              <Input label="Próg sprzedaży (≤)" type="number" value={sell} onChange={e => setSell(e.target.value)} min="0" max="100" />
            </>
          )}
          <div>
            <div className="text-xs font-medium text-muted uppercase tracking-wider mb-1">Okres</div>
            <div className="flex gap-1">
              {(view === 'walkforward' ? ['2y','5y'] : ['1y','2y','5y']).map(p => (
                <button key={p} onClick={() => setPeriod(p)}
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-all border"
                  style={{
                    background:  period === p ? 'rgba(59,130,246,0.2)' : '#1E293B',
                    color:       period === p ? '#3B82F6' : '#64748B',
                    borderColor: period === p ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
                  }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          <Button onClick={run} loading={loading} className="w-full">▶ Uruchom</Button>
        </div>
        {view === 'single' && (
          <p className="text-xs text-muted mt-3">
            Strategia: kup gdy Score DT ≥ {buy} · sprzedaj gdy Score DT ≤ {sell}
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          ⚠ {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Spinner size="lg" />
          <div className="text-sm text-muted">
            {view === 'grid' ? 'Testuję dziesiątki kombinacji progów…' :
             view === 'walkforward' ? 'Analizuję stabilność w czasie…' :
             'Symuluję strategię score…'}
          </div>
        </div>
      )}

      {!loading && single && <SingleBacktest result={single} />}
      {!loading && grid   && <GridHeatmap grid={grid} />}
      {!loading && wf     && <WalkForward wf={wf} />}

      {!loading && !single && !grid && !wf && !error && (
        <EmptyState icon="🧪" title="Skonfiguruj i uruchom backtest"
          desc="Wybierz tryb, instrument i parametry. Pojedynczy test pokazuje krzywą kapitału, heatmapa znajduje optymalne progi, walk-forward sprawdza stabilność reguły w czasie." />
      )}
    </AppShell>
  )
}
