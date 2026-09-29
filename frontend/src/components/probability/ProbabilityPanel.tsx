'use client'

import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts'
import { Info, Target, Activity, ArrowRight, ShieldCheck } from 'lucide-react'
import { Spinner, Button, Input } from '../ui'
import { probabilityApi, type ProbabilityResult, type CalibrationResult } from '../../lib/api'

const DRIFTS = [
  { value: 'zero',       label: 'Zerowy',      desc: 'Brak założenia o kierunku — najuczciwsze dla krótkich horyzontów.' },
  { value: 'shrink',     label: 'Stonowany',   desc: '20% historycznego trendu — przyznaje mu pewną wartość, ale nie ufa bezkrytycznie.' },
  { value: 'historical', label: 'Historyczny', desc: 'Pełny trend z historii. Uwaga: to w dużej mierze szum, nie prognoza.' },
]

const REGIME_COLOR: Record<string, string> = {
  niska: '#22C55E', normalna: '#3B82F6', wysoka: '#F59E0B', ekstremalna: '#EF4444',
}

// ── Wachlarz kwantyli ─────────────────────────────────────────────────

function FanChart({ data }: { data: ProbabilityResult }) {
  const rows = [
    { d: 0, q5: data.last_price, q10: data.last_price, q25: data.last_price,
      q50: data.last_price, q75: data.last_price, q90: data.last_price, q95: data.last_price },
    ...data.bands.map(b => ({ d: b.horizon_days, ...b.quantiles })),
  ]
  // Recharts rysuje warstwy skumulowane, więc przekazujemy szerokości pasm
  const chart = rows.map(r => ({
    d: r.d,
    base: r.q5,
    b5_10:  r.q10 - r.q5,
    b10_25: r.q25 - r.q10,
    b25_50: r.q50 - r.q25,
    b50_75: r.q75 - r.q50,
    b75_90: r.q90 - r.q75,
    b90_95: r.q95 - r.q90,
    mediana: r.q50,
  }))

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <div className="flex items-baseline justify-between mb-3">
        <div className="text-2xs text-muted uppercase tracking-widest">Rozkład możliwych cen</div>
        <div className="text-2xs text-muted">ciemniejsze pasmo = bardziej prawdopodobne</div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chart} margin={{ top: 5, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="d" tick={{ fill: '#64748B', fontSize: 11 }}
            tickFormatter={v => v === 0 ? 'dziś' : `${v}d`} stroke="rgba(255,255,255,0.1)" />
          <YAxis tick={{ fill: '#64748B', fontSize: 11 }} domain={['auto', 'auto']}
            stroke="rgba(255,255,255,0.1)" width={58} />
          <Tooltip
            contentStyle={{ background: '#0B1220', border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: 10, fontSize: 12 }}
            labelFormatter={v => v === 0 ? 'Dziś' : `Za ${v} dni`}
            formatter={(val: any, name: string) =>
              name === 'mediana' ? [Number(val).toFixed(2), 'Mediana'] : null}
          />
          <Area dataKey="base"   stackId="1" stroke="none" fill="transparent" />
          <Area dataKey="b5_10"  stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.08} />
          <Area dataKey="b10_25" stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.16} />
          <Area dataKey="b25_50" stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.28} />
          <Area dataKey="b50_75" stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.28} />
          <Area dataKey="b75_90" stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.16} />
          <Area dataKey="b90_95" stackId="1" stroke="none" fill="#22C55E" fillOpacity={0.08} />
          <Line type="monotone" dataKey="mediana" stroke="#22C55E" strokeWidth={2} dot={false} />
          <ReferenceLine y={data.last_price} stroke="#64748B" strokeDasharray="4 4" />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-2xs text-muted mt-2 leading-relaxed">
        To nie jest prognoza ceny. Wachlarz pokazuje, w jakim zakresie cena może się znaleźć
        i z jakim prawdopodobieństwem — przy założeniach wypisanych na dole strony.
      </p>
    </div>
  )
}

// ── Prognoza zmienności ───────────────────────────────────────────────

function VolChart({ data }: { data: ProbabilityResult }) {
  const path = data.volatility.forecast_path_pct
  if (!path?.length) return null
  const chart = path.map((v, i) => ({ d: i + 1, vol: v }))
  const longrun = data.volatility.garch?.longrun_daily_pct

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <div className="text-2xs text-muted uppercase tracking-widest mb-3">
        Prognoza zmienności dziennej
      </div>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={chart} margin={{ top: 5, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="d" tick={{ fill: '#64748B', fontSize: 10 }}
            tickFormatter={v => `${v}d`} stroke="rgba(255,255,255,0.1)" />
          <YAxis tick={{ fill: '#64748B', fontSize: 10 }} width={46}
            tickFormatter={v => `${v}%`} stroke="rgba(255,255,255,0.1)" />
          <Tooltip contentStyle={{ background: '#0B1220', border: '1px solid rgba(255,255,255,0.1)',
                                   borderRadius: 10, fontSize: 12 }}
            formatter={(v: any) => [`${Number(v).toFixed(3)}%`, 'Zmienność']}
            labelFormatter={v => `Dzień ${v}`} />
          <Line type="monotone" dataKey="vol" stroke="#F59E0B" strokeWidth={2} dot={false} />
          {longrun && <ReferenceLine y={longrun} stroke="#64748B" strokeDasharray="4 4" />}
        </LineChart>
      </ResponsiveContainer>
      {longrun && (
        <p className="text-2xs text-muted mt-1.5 leading-relaxed">
          Przerywana linia to długoterminowa zmienność instrumentu ({longrun.toFixed(2)}%).
          Model GARCH zakłada powrót do niej — po gwałtownym ruchu rynek zwykle się uspokaja.
        </p>
      )}
    </div>
  )
}

// ── Kalkulator poziomu ────────────────────────────────────────────────

function LevelCalculator({ ticker, lastPrice, drift }: { ticker: string; lastPrice: number; drift: string }) {
  const [input, setInput] = useState('')
  const [level, setLevel] = useState<number | null>(null)
  const { data, isLoading } = useSWR(
    level ? ['prob-level', ticker, level, drift] : null,
    () => probabilityApi.get(ticker, { level: level!, drift }),
    { revalidateOnFocus: false },
  )

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <div className="flex items-center gap-2 mb-1">
        <Target className="w-4 h-4 text-brand-green" />
        <div className="text-sm font-semibold text-text-hi">Kalkulator prawdopodobieństw</div>
      </div>
      <p className="text-xs text-text-lo mb-3 leading-relaxed">
        Sprawdź szansę, że cena <strong className="text-text-mid">dotknie</strong> wybranego poziomu —
        przydatne przy ustawianiu stop-lossa lub celu. Dotknięcie w trakcie to co innego niż
        zamknięcie powyżej/poniżej.
      </p>
      <div className="flex gap-2 mb-3">
        <Input type="number" step="any" value={input} onChange={e => setInput(e.target.value)}
          placeholder={`np. ${(lastPrice * 1.05).toFixed(2)}`} className="max-w-[180px]" />
        <Button size="sm" onClick={() => { const v = parseFloat(input); if (v > 0) setLevel(v) }}>
          Sprawdź
        </Button>
      </div>

      {isLoading && <Spinner size="sm" />}
      {data?.level_query && (
        <div className="space-y-1.5 animate-fade-in">
          <div className="text-2xs text-muted">
            Poziom <span className="font-mono text-text-hi">{data.level_query.level}</span>
            {' '}({((data.level_query.level / lastPrice - 1) * 100).toFixed(1)}% od bieżącej)
          </div>
          {data.level_query.by_horizon.map(h => (
            <div key={h.horizon_days} className="flex items-center gap-3 text-xs">
              <span className="text-muted w-14">{h.horizon_days} dni</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <div className="h-full rounded-full"
                  style={{ width: `${Math.min(100, h.prob_touch_pct)}%`, background: '#22C55E' }} />
              </div>
              <span className="font-mono font-bold w-12 text-right" style={{ color: '#22C55E' }}>
                {h.prob_touch_pct}%
              </span>
            </div>
          ))}
          <p className="text-2xs text-muted pt-1">Szansa dotknięcia w dowolnym momencie horyzontu.</p>
        </div>
      )}
    </div>
  )
}

// ── Tablica kalibracji ────────────────────────────────────────────────

function CalibrationPanel() {
  const { data } = useSWR<CalibrationResult>('prob-calibration', probabilityApi.calibration,
    { revalidateOnFocus: false })
  if (!data) return null

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <div className="flex items-center gap-2 mb-1">
        <ShieldCheck className="w-4 h-4 text-brand-green" />
        <div className="text-sm font-semibold text-text-hi">Jak często mamy rację</div>
      </div>
      {!data.ready ? (
        <p className="text-xs text-text-lo leading-relaxed">{data.message}</p>
      ) : (
        <>
          <p className="text-xs text-text-lo mb-3 leading-relaxed">
            Faktyczne pokrycie przedziałów na {data.resolved_forecasts} rozstrzygniętych prognozach.
            Im bliżej deklarowanej wartości, tym lepiej skalibrowany model.
          </p>
          <div className="space-y-1.5">
            {data.coverage.map(c => {
              const diff = c.actual_pct != null ? Math.abs(c.actual_pct - c.declared_pct) : null
              const col = diff == null ? '#64748B' : diff <= 3 ? '#22C55E' : diff <= 7 ? '#F59E0B' : '#EF4444'
              return (
                <div key={c.declared_pct} className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-muted w-20">deklarowane {c.declared_pct}%</span>
                  <ArrowRight className="w-3 h-3 text-muted" />
                  <span className="font-bold" style={{ color: col }}>{c.actual_pct}%</span>
                  <span className="text-2xs text-muted">({c.sample} prognoz)</span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ── Panel do osadzenia w zakładce Analizy ─────────────────────────────

export function ProbabilityPanel({ ticker }: { ticker: string }) {
  const [drift, setDrift] = useState('zero')

  const { data, isLoading, error } = useSWR(
    ticker ? ['probability', ticker, drift] : null,
    () => probabilityApi.get(ticker, { drift }),
    { revalidateOnFocus: false },
  )

  return (
    <div>
      <div className="flex items-start gap-2.5 mb-5 text-xs text-text-lo bg-surface-1 border border-border rounded-xl p-3">
        <Info className="w-4 h-4 text-muted shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          Silnik <strong className="text-text-mid">nie przewiduje ceny</strong> — buduje rozkład
          możliwych scenariuszy i podaje prawdopodobieństwa, które da się sprawdzić.
          Zmienność liczona estymatorem Yang-Zhang z pełnych świec, dynamika modelem GARCH,
          szoki z rozkładu o grubych ogonach. To znacznie ostrożniejsze podejście niż
          klasyczna symulacja z rozkładem normalnym.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
          {(error as any)?.detail ?? 'Nie udało się zbudować rozkładu dla tego instrumentu.'}
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col items-center py-16 gap-3">
          <Spinner size="lg" />
          <span className="text-sm text-muted">Symuluję 10 000 ścieżek cenowych…</span>
        </div>
      )}

      {data && !isLoading && (
        <div className="space-y-4 animate-fade-in">
          {/* Nagłówek instrumentu */}
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <div>
              <span className="text-lg font-bold font-mono text-text-hi">{data.ticker}</span>
              <span className="text-sm text-muted ml-2">{data.last_price}</span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5" style={{ color: REGIME_COLOR[data.regime.label] ?? '#64748B' }} />
              <span className="text-xs text-muted">Zmienność:</span>
              <span className="text-xs font-semibold" style={{ color: REGIME_COLOR[data.regime.label] ?? '#64748B' }}>
                {data.regime.label}
              </span>
              {data.regime.percentile != null && (
                <span className="text-2xs text-muted">({data.regime.percentile} percentyl własnej historii)</span>
              )}
            </div>
            <div className="text-xs text-muted">
              Roczna: <span className="font-mono text-text-lo">{data.volatility.annualized_pct}%</span>
            </div>
          </div>

          {/* Wybór dryfu */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-2xs text-muted uppercase tracking-wider">Założenie o trendzie:</span>
            {DRIFTS.map(d => (
              <button key={d.value} onClick={() => setDrift(d.value)} title={d.desc}
                className="px-3 py-1 rounded-lg text-xs font-medium transition-all border"
                style={{
                  background:  drift === d.value ? 'rgba(34,197,94,0.18)' : '#141C2B',
                  color:       drift === d.value ? '#22C55E' : '#64748B',
                  borderColor: drift === d.value ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.06)',
                }}>
                {d.label}
              </button>
            ))}
          </div>

          <FanChart data={data} />

          {/* Tabela kwantyli */}
          <div className="bg-surface-1 border border-border rounded-xl2 p-4 overflow-x-auto">
            <div className="text-2xs text-muted uppercase tracking-widest mb-3">Poziomy cenowe</div>
            <table className="w-full border-collapse min-w-[520px]">
              <thead>
                <tr className="text-2xs text-muted uppercase tracking-wider">
                  <th className="text-left pb-2">Horyzont</th>
                  <th className="text-right pb-2">Bardzo nisko (5%)</th>
                  <th className="text-right pb-2">Nisko (25%)</th>
                  <th className="text-right pb-2">Mediana</th>
                  <th className="text-right pb-2">Wysoko (75%)</th>
                  <th className="text-right pb-2">Bardzo wysoko (95%)</th>
                </tr>
              </thead>
              <tbody>
                {data.bands.map(b => (
                  <tr key={b.horizon_days} className="border-t border-border">
                    <td className="py-2 text-xs text-text-lo">{b.horizon_days} dni</td>
                    <td className="py-2 text-right text-xs font-mono" style={{ color: '#EF4444' }}>{b.quantiles.q5}</td>
                    <td className="py-2 text-right text-xs font-mono text-text-lo">{b.quantiles.q25}</td>
                    <td className="py-2 text-right text-sm font-mono font-bold text-text-hi">{b.quantiles.q50}</td>
                    <td className="py-2 text-right text-xs font-mono text-text-lo">{b.quantiles.q75}</td>
                    <td className="py-2 text-right text-xs font-mono" style={{ color: '#22C55E' }}>{b.quantiles.q95}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-2xs text-muted mt-2">
              „Mediana" to środek rozkładu, nie prognoza — połowa scenariuszy wypada powyżej, połowa poniżej.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <VolChart data={data} />

            {/* Prawdopodobieństwa ruchu */}
            <div className="bg-surface-1 border border-border rounded-xl2 p-4">
              <div className="text-2xs text-muted uppercase tracking-widest mb-3">
                Szansa dotknięcia w 20 dni
              </div>
              <div className="space-y-2">
                {[5, 10, 20].map(pct => {
                  const up = data.move_probabilities[`up_${pct}pct_20d`] ?? 0
                  const dn = data.move_probabilities[`down_${pct}pct_20d`] ?? 0
                  return (
                    <div key={pct} className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-bold w-10 text-right" style={{ color: '#22C55E' }}>{up}%</span>
                      <div className="flex-1 flex gap-0.5 h-1.5">
                        <div className="flex-1 flex justify-end rounded-l-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                          <div style={{ width: `${Math.min(100, up)}%`, background: '#22C55E' }} />
                        </div>
                        <div className="flex-1 rounded-r-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                          <div style={{ width: `${Math.min(100, dn)}%`, background: '#EF4444' }} />
                        </div>
                      </div>
                      <span className="font-mono font-bold w-10" style={{ color: '#EF4444' }}>{dn}%</span>
                      <span className="text-2xs text-muted w-10">±{pct}%</span>
                    </div>
                  )
                })}
              </div>
              {data.daily_range.median_range_pct && (
                <div className="mt-3 pt-3 border-t border-border text-xs text-text-lo">
                  Typowy zakres dzienny: <span className="font-mono text-text-hi">{data.daily_range.median_range_pct}%</span>
                  {data.daily_range.p90_range_pct && (
                    <span className="text-muted"> · w 10% dni przekracza {data.daily_range.p90_range_pct}%</span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <LevelCalculator ticker={data.ticker} lastPrice={data.last_price} drift={drift} />
            <CalibrationPanel />
          </div>

          {/* Założenia — jawnie, bo ukrywanie ich wygląda na magię */}
          <div className="bg-surface-1 border border-border rounded-xl2 p-4">
            <div className="text-2xs text-muted uppercase tracking-widest mb-2">Co ten model zakłada</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-muted">Estymator zmienności</span>
                <span className="text-text-lo font-mono">{data.assumptions.volatility_estimator}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Rozkład szoków</span>
                <span className="text-text-lo font-mono text-right">{data.assumptions.distribution}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Liczba symulacji</span>
                <span className="text-text-lo font-mono">{data.assumptions.simulations.toLocaleString('pl-PL')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Grubość ogonów (ν)</span>
                <span className="text-text-lo font-mono">{data.tail_fatness_nu}</span>
              </div>
              {data.volatility.garch && (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted">GARCH persistence</span>
                    <span className="text-text-lo font-mono">{data.volatility.garch.persistence}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Zmienność długoterminowa</span>
                    <span className="text-text-lo font-mono">{data.volatility.garch.longrun_daily_pct}% dziennie</span>
                  </div>
                </>
              )}
              <div className="flex justify-between">
                <span className="text-muted">Wersja modelu</span>
                <span className="text-text-lo font-mono">{data.model_version}</span>
              </div>
            </div>
            <p className="text-2xs text-muted mt-3 pt-3 border-t border-border leading-relaxed">
              Model zakłada, że przyszłość przypomina przeszłość pod względem charakteru zmienności.
              Nie uwzględnia zdarzeń, których nie było w danych: przejęć, zmian regulacyjnych,
              szoków makro. Rozkład to narzędzie oceny ryzyka, nie rekomendacja inwestycyjna.
            </p>
            <Link href={`/analysis?ticker=${data.ticker}`}
              className="inline-flex items-center gap-1 text-xs text-brand-green hover:underline mt-3">
              Pełna analiza {data.ticker} <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
