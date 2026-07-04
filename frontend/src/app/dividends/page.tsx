'use client'

import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { Coins, ArrowRight, TrendingUp, TrendingDown, ShieldCheck } from 'lucide-react'
import { AppShell } from '../../components/layout/AppShell'
import { scoreColor } from '../../components/ui/ScoreBadge'
import { Spinner } from '../../components/ui'
import { dividendsApi, type DividendStock, type DividendFlag } from '../../lib/api'

// ── Kolory flag ───────────────────────────────────────────────────────

function flagStyle(typ: DividendFlag[0]) {
  switch (typ) {
    case 'pozytyw':     return { bg: 'rgba(34,197,94,0.12)',  color: '#22C55E' }
    case 'ostrzezenie': return { bg: 'rgba(239,68,68,0.12)',  color: '#F87171' }
    default:            return { bg: 'rgba(148,163,184,0.12)', color: '#94A3B8' }
  }
}

// ── Mini-pasek filaru ─────────────────────────────────────────────────

function FilarBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-2xs text-muted w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: scoreColor(value) }} />
      </div>
      <span className="text-2xs font-mono tabular-nums w-6 text-right" style={{ color: scoreColor(value) }}>
        {Math.round(value)}
      </span>
    </div>
  )
}

// ── Wiersz rankingu ───────────────────────────────────────────────────

function DividendRow({ stock, rank }: { stock: DividendStock; rank: number }) {
  const [expanded, setExpanded] = useState(false)
  const trendIcon = stock.trend === 'rosnacy'
    ? <TrendingUp className="w-3.5 h-3.5" style={{ color: '#22C55E' }} />
    : stock.trend === 'malejacy'
    ? <TrendingDown className="w-3.5 h-3.5" style={{ color: '#F87171' }} />
    : null

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden hover:border-border-hi transition-all">
      <button onClick={() => setExpanded(e => !e)} className="w-full text-left">
        <div className="flex items-center gap-4 p-4">
          {/* Rank + score */}
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-sm font-mono text-muted w-5 text-center tabular-nums">{rank}</span>
            <div className="w-11 h-11 rounded-xl flex flex-col items-center justify-center shrink-0"
              style={{ background: `${scoreColor(stock.score)}1a`, border: `1px solid ${scoreColor(stock.score)}40` }}>
              <span className="text-sm font-bold font-mono leading-none" style={{ color: scoreColor(stock.score) }}>
                {Math.round(stock.score)}
              </span>
              <span className="text-[8px] text-muted uppercase tracking-wide mt-0.5">score</span>
            </div>
          </div>

          {/* Nazwa */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-bold font-mono text-sm text-text-hi">{stock.ticker}</span>
              {trendIcon}
            </div>
            <div className="text-xs text-muted truncate">{stock.nazwa}</div>
          </div>

          {/* Stopa brutto -> netto (SYGNATURA) */}
          <div className="text-right shrink-0">
            <div className="flex items-baseline gap-1 justify-end">
              <span className="text-lg font-bold font-mono tabular-nums" style={{ color: '#22C55E' }}>
                {stock.yield_brutto != null ? `${stock.yield_brutto}%` : '—'}
              </span>
              <span className="text-2xs text-muted">brutto</span>
            </div>
            {stock.yield_netto != null && (
              <div className="text-2xs text-muted font-mono">
                {stock.yield_netto}% netto (po Belce)
              </div>
            )}
          </div>

          {/* Lata ciągłości */}
          <div className="text-right shrink-0 hidden sm:block w-16">
            <div className="text-sm font-mono font-bold text-text-hi tabular-nums">{stock.lata_ciaglosci}</div>
            <div className="text-2xs text-muted">lat z rzędu</div>
          </div>

          <span className="text-muted text-xs shrink-0">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Rozwinięcie */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-border animate-fade-in space-y-3">
          <p className="text-sm text-text-lo">{stock.opis}</p>

          {/* Trzy filary */}
          <div className="space-y-1.5 max-w-md">
            <FilarBar label="Bezpieczeństwo" value={stock._filary.bezpieczenstwo} />
            <FilarBar label="Ciągłość" value={stock._filary.ciaglosc} />
            <FilarBar label="Atrakcyjność" value={stock._filary.atrakcyjnosc} />
          </div>

          {/* Flagi */}
          {stock.flagi.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {stock.flagi.map(([typ, tekst], i) => {
                const s = flagStyle(typ)
                return (
                  <span key={i} className="text-2xs px-2 py-0.5 rounded-md font-medium"
                    style={{ background: s.bg, color: s.color }}>
                    {tekst}
                  </span>
                )
              })}
            </div>
          )}

          {/* Meta + link */}
          <div className="flex items-center justify-between pt-1 text-2xs text-muted">
            <div className="flex gap-4 flex-wrap">
              {stock.dywidenda_roczna != null && <span>Dywidenda roczna: <span className="font-mono text-text-lo">{stock.dywidenda_roczna} PLN</span></span>}
              {stock.payout_ratio != null && <span>Payout: <span className="font-mono text-text-lo">{Math.round(stock.payout_ratio * 100)}%</span></span>}
              {stock.ostatnia_wyplata && <span>Ostatnia wypłata: <span className="font-mono text-text-lo">{stock.ostatnia_wyplata}</span></span>}
            </div>
            <Link href={`/analysis?ticker=${stock.ticker}`}
              className="flex items-center gap-1 text-brand-green hover:underline shrink-0">
              Pełna analiza <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Strona ────────────────────────────────────────────────────────────

export default function DividendsPage() {
  const { data, isLoading } = useSWR('dividends', dividendsApi.get, {
    revalidateOnFocus: false,
  })
  const [minStopa, setMinStopa] = useState(0)

  const filtrowane = (data?.placace ?? []).filter(
    s => s.yield_brutto == null || s.yield_brutto >= minStopa
  )

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Coins className="w-5 h-5 text-brand-green" /> Dywidendy GPW
        </h1>
        {data?.statystyki.srednia_stopa_brutto != null && (
          <span className="text-sm text-muted">
            Średnia stopa: <span className="font-mono font-bold" style={{ color: '#22C55E' }}>
              {data.statystyki.srednia_stopa_brutto}%
            </span>
          </span>
        )}
      </div>

      {/* Wyjaśnienie */}
      <div className="flex items-start gap-2.5 mb-5 text-xs text-text-lo bg-surface-1 border border-border rounded-xl p-3">
        <ShieldCheck className="w-4 h-4 text-muted shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          Ranking spółek według <strong className="text-text-mid">score dywidendowego</strong> — liczonego
          z historii wypłat, nie z pojedynczej migawki. Score łączy trzy obszary:
          <strong className="text-text-mid"> bezpieczeństwo</strong> dywidendy (40%),
          <strong className="text-text-mid"> ciągłość i wzrost</strong> wypłat (35%) oraz
          <strong className="text-text-mid"> atrakcyjność</strong> stopy (25%).
          Stopę pokazujemy brutto oraz <strong className="text-text-mid">netto po podatku Belki (19%)</strong> —
          czyli to, co realnie trafia do kieszeni.
        </p>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Spinner size="lg" />
          <span className="text-sm text-muted">Analizuję historię wypłat spółek…</span>
        </div>
      ) : !data ? (
        <div className="text-center py-16 text-muted">
          Nie udało się pobrać danych. Odśwież stronę, aby spróbować ponownie.
        </div>
      ) : (
        <>
          {/* Filtr min. stopy */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xs text-muted uppercase tracking-wider">Min. stopa brutto:</span>
            {[0, 3, 5, 7].map(v => (
              <button key={v} onClick={() => setMinStopa(v)}
                className="px-3 py-1 rounded-lg text-xs font-medium transition-all border"
                style={{
                  background:  minStopa === v ? 'rgba(34,197,94,0.18)' : '#141C2B',
                  color:       minStopa === v ? '#22C55E' : '#64748B',
                  borderColor: minStopa === v ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.06)',
                }}>
                {v === 0 ? 'Wszystkie' : `${v}%+`}
              </button>
            ))}
          </div>

          {/* Ranking */}
          <div className="space-y-2">
            {filtrowane.map((stock, i) => (
              <DividendRow key={stock.ticker} stock={stock} rank={i + 1} />
            ))}
          </div>

          {filtrowane.length === 0 && (
            <div className="text-center py-10 text-muted text-sm">
              Żadna spółka nie spełnia wybranego progu stopy.
            </div>
          )}

          {/* Spółki niewypłacające */}
          {data.niewyplacajace.length > 0 && (
            <div className="mt-8">
              <div className="text-2xs text-muted uppercase tracking-widest mb-2">
                Nie wypłacają dywidendy
              </div>
              <div className="flex flex-wrap gap-2">
                {data.niewyplacajace.map(s => (
                  <Link key={s.ticker} href={`/analysis?ticker=${s.ticker}`}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-1 border border-border hover:bg-surface-2 transition-all text-xs">
                    <span className="font-mono font-bold text-text-lo">{s.ticker}</span>
                    <span className="text-muted">{s.nazwa}</span>
                  </Link>
                ))}
              </div>
              <p className="text-2xs text-muted mt-2">
                Te spółki nie wypłacają dywidend — często reinwestują zysk we wzrost. To nie jest wada, to inna strategia.
              </p>
            </div>
          )}

          <p className="text-2xs text-muted mt-6 pt-4 border-t border-border">
            Score dywidendowy to narzędzie edukacyjne, nie rekomendacja inwestycyjna.
            Wysoka stopa dywidendy bywa sygnałem ryzyka, nie tylko okazji — dlatego bezpieczeństwo waży najwięcej.
          </p>
        </>
      )}
    </AppShell>
  )
}
