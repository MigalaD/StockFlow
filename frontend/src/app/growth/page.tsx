'use client'

import { useState, useMemo } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { Rocket, ArrowRight, Info } from 'lucide-react'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBadge, scoreColor } from '../../components/ui/ScoreBadge'
import { Spinner, Price, Tag } from '../../components/ui'
import { growthApi, type GrowthStock } from '../../lib/api'

// ── Karta spółki ──────────────────────────────────────────────────────

function GrowthCard({ stock }: { stock: GrowthStock }) {
  return (
    <Link href={`/analysis?ticker=${stock.ticker}`}
      className="block bg-surface-1 border border-border rounded-xl2 p-4 hover:bg-surface-2 hover:border-border-hi transition-all group">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold font-mono text-sm text-text-hi group-hover:text-brand-green transition-colors">
              {stock.ticker}
            </span>
            <Tag>{stock.category}</Tag>
          </div>
          <div className="text-xs text-muted truncate mt-0.5">{stock.name}</div>
        </div>
        <ScoreBadge score={stock.score} size="sm" />
      </div>

      <p className="text-xs text-text-lo leading-relaxed mb-3 line-clamp-2">
        {stock.description}
      </p>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <Price value={stock.price} currency={stock.currency}
          className="text-sm font-semibold text-text-hi" />
        <span className="flex items-center gap-1 text-2xs text-muted group-hover:text-brand-green transition-colors">
          Analizuj <ArrowRight className="w-3 h-3" />
        </span>
      </div>
    </Link>
  )
}

// ── Strona ────────────────────────────────────────────────────────────

export default function GrowthPage() {
  const { data, isLoading } = useSWR('growth', growthApi.get, {
    revalidateOnFocus: false,
  })
  const [activeCat, setActiveCat] = useState<string>('all')

  const filtered = useMemo(() => {
    if (!data) return []
    if (activeCat === 'all') return data.stocks
    return data.stocks.filter(s => s.category === activeCat)
  }, [data, activeCat])

  const avgScore = data?.stocks.length
    ? Math.round(data.stocks.reduce((s, x) => s + x.score, 0) / data.stocks.length)
    : null

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Rocket className="w-5 h-5 text-brand-green" /> Spółki wzrostowe
        </h1>
        {avgScore != null && (
          <span className="text-sm text-muted">
            Średni score: <span className="font-mono font-bold" style={{ color: scoreColor(avgScore) }}>{avgScore}</span>
          </span>
        )}
      </div>

      {/* Wyjaśnienie */}
      <div className="flex items-start gap-2.5 mb-5 text-xs text-text-lo bg-surface-1 border border-border rounded-xl p-3">
        <Info className="w-4 h-4 text-muted shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          To <strong className="text-text-mid">nie prywatne startupy</strong> — dane firm przed IPO nie są publiczne.
          To spółki już notowane na giełdzie, często po niedawnym debiucie lub w fazie szybkiego wzrostu.
          Zwykle <strong className="text-text-mid">bardziej zmienne i ryzykowne</strong> niż duże, ugruntowane firmy.
        </p>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Spinner size="lg" />
          <span className="text-sm text-muted">Analizuję spółki wzrostowe…</span>
        </div>
      ) : !data || data.stocks.length === 0 ? (
        <div className="text-center py-16 text-muted">
          Nie udało się pobrać danych. Spróbuj odświeżyć stronę.
        </div>
      ) : (
        <>
          {/* Filtry kategorii */}
          <div className="flex gap-1.5 flex-wrap mb-5">
            <button
              onClick={() => setActiveCat('all')}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all border"
              style={{
                background:  activeCat === 'all' ? 'rgba(34,197,94,0.18)' : '#141C2B',
                color:       activeCat === 'all' ? '#22C55E' : '#64748B',
                borderColor: activeCat === 'all' ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.06)',
              }}
            >
              Wszystkie <span className="opacity-60">({data.stocks.length})</span>
            </button>
            {data.categories.map(cat => {
              const count = data.stocks.filter(s => s.category === cat).length
              return (
                <button
                  key={cat}
                  onClick={() => setActiveCat(cat)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all border"
                  style={{
                    background:  activeCat === cat ? 'rgba(34,197,94,0.18)' : '#141C2B',
                    color:       activeCat === cat ? '#22C55E' : '#64748B',
                    borderColor: activeCat === cat ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.06)',
                  }}
                >
                  {cat} <span className="opacity-60">({count})</span>
                </button>
              )
            })}
          </div>

          {/* Siatka kart */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map(stock => (
              <GrowthCard key={stock.ticker} stock={stock} />
            ))}
          </div>
        </>
      )}
    </AppShell>
  )
}
