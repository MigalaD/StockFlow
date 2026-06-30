'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBadge, scoreColor } from '../../components/ui/ScoreBadge'
import { Button, Input, EmptyState, Spinner, SectionHeader, Tag, Price } from '../../components/ui'
import { analysisApi, type AnalysisResult } from '../../lib/api'

const MAX_INSTRUMENTS = 6

const COMPARE_COLORS = ['#22C55E','#14B8A6','#3B82F6','#F59E0B','#8B5CF6','#EC4899']

function CompareHeader({
  results,
  onRemove,
}: {
  results: AnalysisResult[]
  onRemove: (ticker: string) => void
}) {
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${results.length}, 1fr)` }}>
      {results.map((r, i) => {
        const color = COMPARE_COLORS[i]
        return (
          <div
            key={r.ticker}
            className="bg-surface-1 border border-border rounded-xl2 p-4 text-center hover:bg-surface-2 transition-colors"
            style={{ borderTop: `2px solid ${color}` }}
          >
            <div className="flex justify-end mb-1">
              <button
                onClick={() => onRemove(r.ticker)}
                className="text-muted hover:text-red-400 text-xs transition-colors"
              >✕</button>
            </div>
            <div className="font-bold text-text-hi mb-0.5 font-mono">{r.ticker}</div>
            <div className="text-xs text-muted mb-3 truncate">{r.name}</div>
            <ScoreBadge score={r.total_score} size="lg" showLabel />
            <div className="mt-3">
              <Price value={r.price} currency={r.currency}
                className="text-2xl font-bold text-text-hi" />
            </div>
            {r.sector && <Tag className="mt-2 text-muted">{r.sector}</Tag>}
          </div>
        )
      })}
    </div>
  )
}

function RadarComparison({ results }: { results: AnalysisResult[] }) {
  // Zbierz wspólne klucze komponentów
  const allKeys = Array.from(
    new Set(results.flatMap(r => r.components.map(c => c.key)))
  ).slice(0, 8)

  const data = allKeys.map(key => {
    const entry: Record<string, any> = { key }
    results.forEach((r, i) => {
      const comp = r.components.find(c => c.key === key)
      entry[r.ticker] = comp ? Math.round(comp.score) : 0
    })
    return entry
  })

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <SectionHeader title="Porównanie składowych" icon="🕸" />
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.07)" />
          <PolarAngleAxis
            dataKey="key"
            tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'Inter' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#64748B', fontSize: 9 }}
          />
          {results.map((r, i) => (
            <Radar
              key={r.ticker}
              name={r.ticker}
              dataKey={r.ticker}
              stroke={COMPARE_COLORS[i]}
              fill={COMPARE_COLORS[i]}
              fillOpacity={0.08}
              strokeWidth={2}
            />
          ))}
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(v) => <span style={{ color: '#94A3B8', fontSize: 11 }}>{v}</span>}
          />
          <Tooltip
            contentStyle={{ background: '#0F1623', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
            labelStyle={{ color: '#F8FAFC', fontWeight: 600 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ScoreHistoryComparison({ tickers }: { tickers: string[] }) {
  const [histories, setHistories] = useState<Record<string, { date: string; score: number }[]>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!tickers.length) return
    setLoading(true)
    Promise.allSettled(
      tickers.map(t => analysisApi.history(t, 90).then(h => ({ ticker: t, data: h })))
    ).then(results => {
      const map: typeof histories = {}
      results.forEach(r => {
        if (r.status === 'fulfilled') map[r.value.ticker] = r.value.data
      })
      setHistories(map)
      setLoading(false)
    })
  }, [tickers.join(',')])

  // Zunifikuj daty
  const allDates = Array.from(
    new Set(Object.values(histories).flatMap(h => h.map(p => p.date)))
  ).sort()

  if (!allDates.length) return null

  const chartData = allDates.slice(-60).map(date => {
    const entry: Record<string, any> = { date: date.slice(5) } // MM-DD
    tickers.forEach(ticker => {
      const point = histories[ticker]?.find(p => p.date === date)
      if (point) entry[ticker] = Math.round(point.score)
    })
    return entry
  })

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <SectionHeader title="Historia score (90 dni)" icon="📈" />
      {loading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 10 }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: '#64748B', fontSize: 10 }} tickLine={false} width={28} />
            <Tooltip
              contentStyle={{ background: '#0F1623', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
              labelStyle={{ color: '#F8FAFC' }}
            />
            <Legend
              iconType="circle" iconSize={8}
              formatter={(v) => <span style={{ color: '#94A3B8', fontSize: 11 }}>{v}</span>}
            />
            {tickers.map((ticker, i) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stroke={COMPARE_COLORS[i]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function ComponentsTable({ results }: { results: AnalysisResult[] }) {
  const allKeys = Array.from(
    new Set(results.flatMap(r => r.components.map(c => c.key)))
  )

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden p-4">
      <SectionHeader title="Tabela składowych" icon="📊" />
      <table className="w-full border-collapse">
        <thead>
          <tr style={{ backgroundColor: '#0B1120' }}>
            <th className="px-4 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border">
              Wskaźnik
            </th>
            {results.map((r, i) => (
              <th
                key={r.ticker}
                className="px-4 py-2.5 text-center text-[10px] uppercase tracking-wider font-semibold border-b border-border"
                style={{ color: COMPARE_COLORS[i] }}
              >
                {r.ticker}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {allKeys.map(key => {
            const scores = results.map(r => r.components.find(c => c.key === key)?.score ?? null)
            const validScores = scores.filter(s => s !== null) as number[]
            const maxScore = validScores.length ? Math.max(...validScores) : null

            return (
              <tr key={key} className="border-b border-border hover:bg-surface-2">
                <td className="px-4 py-2.5 text-xs font-medium text-text-mid">{key}</td>
                {scores.map((score, i) => (
                  <td key={i} className="px-4 py-2.5 text-center">
                    {score != null ? (
                      <span
                        className="font-bold font-mono tabular-nums text-sm"
                        style={{
                          color: scoreColor(score),
                          fontWeight: score === maxScore ? 700 : 400,
                        }}
                      >
                        {Math.round(score)}
                        {score === maxScore && validScores.length > 1 && (
                          <span className="text-[10px] ml-0.5">★</span>
                        )}
                      </span>
                    ) : (
                      <span className="text-muted text-xs">—</span>
                    )}
                  </td>
                ))}
              </tr>
            )
          })}
          {/* Podsumowanie */}
          <tr className="border-t-2" style={{ borderColor: 'rgba(255,255,255,0.12)', background: '#0B1120' }}>
            <td className="px-4 py-3 text-xs font-bold text-text-hi uppercase tracking-wide">Score DT</td>
            {results.map((r, i) => {
              const isTop = r.total_score === Math.max(...results.map(x => x.total_score))
              return (
                <td key={r.ticker} className="px-4 py-3 text-center">
                  <span
                    className="text-base font-bold font-mono tabular-nums"
                    style={{ color: COMPARE_COLORS[i] }}
                  >
                    {Math.round(r.total_score)}
                    {isTop && results.length > 1 && <span className="text-[10px] ml-0.5">★</span>}
                  </span>
                </td>
              )
            })}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export default function ComparePage() {
  const [inputTicker, setInputTicker] = useState('')
  const [tickers,     setTickers]     = useState<string[]>([])
  const [results,     setResults]     = useState<AnalysisResult[]>([])
  const [loading,     setLoading]     = useState<Record<string, boolean>>({})
  const [errors,      setErrors]      = useState<Record<string, string>>({})

  async function addTicker() {
    const t = inputTicker.trim().toUpperCase()
    if (!t || tickers.includes(t) || tickers.length >= MAX_INSTRUMENTS) return
    setInputTicker('')
    setLoading(prev => ({ ...prev, [t]: true }))
    setErrors(prev => ({ ...prev, [t]: '' }))
    try {
      const data = await analysisApi.analyze(t)
      setTickers(prev => [...prev, t])
      setResults(prev => [...prev, data])
    } catch {
      setErrors(prev => ({ ...prev, [t]: `Brak danych dla ${t}` }))
    } finally {
      setLoading(prev => ({ ...prev, [t]: false }))
    }
  }

  function removeTicker(ticker: string) {
    setTickers(prev => prev.filter(t => t !== ticker))
    setResults(prev => prev.filter(r => r.ticker !== ticker))
  }

  const isLoading = Object.values(loading).some(Boolean)
  const errorList = Object.entries(errors).filter(([, v]) => v)

  return (
    <AppShell>
      <h1 className="text-xl font-bold mb-5">🔀 Porównanie instrumentów</h1>

      {/* Add ticker form */}
      <div className="flex gap-2 mb-5 max-w-lg">
        <Input
          placeholder="Symbol (np. AAPL, CDR.WA, BTC-USD)"
          value={inputTicker}
          onChange={e => setInputTicker(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && addTicker()}
          hint={`Maksymalnie ${MAX_INSTRUMENTS} instrumentów · Enter aby dodać`}
          className="flex-1"
        />
        <Button
          onClick={addTicker}
          loading={isLoading}
          disabled={!inputTicker.trim() || tickers.length >= MAX_INSTRUMENTS}
          className="shrink-0"
        >
          Dodaj
        </Button>
      </div>

      {/* Error messages */}
      {errorList.map(([ticker, err]) => (
        <div
          key={ticker}
          className="mb-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2"
        >
          ⚠ {err}
        </div>
      ))}

      {/* Empty state */}
      {results.length === 0 ? (
        <EmptyState
          icon="🔀"
          title="Wybierz instrumenty do porównania"
          desc="Wpisz symbole w polu powyżej i wciśnij Enter. Możesz porównać do 6 instrumentów naraz — akcje, ETF-y, kryptowaluty i surowce."
          action={
            <div className="flex gap-2 flex-wrap justify-center">
              {['AAPL', 'MSFT', 'NVDA'].map(t => (
                <button
                  key={t}
                  onClick={() => { setInputTicker(t); }}
                  className="text-xs px-3 py-1.5 rounded-full border border-border text-muted hover:border-brand-green hover:text-brand-green transition-colors"
                >
                  {t}
                </button>
              ))}
            </div>
          }
        />
      ) : results.length === 1 ? (
        <div className="mb-5">
          <CompareHeader results={results} onRemove={removeTicker} />
          <div className="mt-4 text-center text-sm text-muted">
            Dodaj przynajmniej jeszcze jeden instrument aby zobaczyć porównanie.
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <CompareHeader results={results} onRemove={removeTicker} />
          <div className="grid grid-cols-2 gap-5">
            <RadarComparison results={results} />
            <ScoreHistoryComparison tickers={tickers} />
          </div>
          <ComponentsTable results={results} />
          <p className="text-xs text-muted text-center">
            ★ = najwyższy wynik w danej kategorii · Score nie jest prognozą ani poradą inwestycyjną
          </p>
        </div>
      )}
    </AppShell>
  )
}
