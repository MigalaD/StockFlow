'use client'

import type { ReactNode } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { AlertTriangle, CalendarDays, Coins, BarChart3 } from 'lucide-react'
import type { AnalysisResult } from '../../lib/api'

// Panel boczny analizy. Każda karta renderuje się tylko wtedy, gdy ma dane —
// zamiast rzędów „—" panel po prostu robi się krótszy.

const INDEX_NAMES: Record<string, string> = { '^GSPC': 'S&P 500', 'WIG20.WA': 'WIG20' }
const GREEN = '#22C55E'
const RED   = '#EF4444'

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="bg-surface-1 border border-border rounded-xl2 p-4">
      <h3 className="text-xs font-semibold text-text-mid mb-3">{title}</h3>
      {children}
    </section>
  )
}

function daysUntil(iso: string): number | null {
  const d = new Date(iso.slice(0, 10) + 'T00:00:00')
  if (Number.isNaN(d.getTime())) return null
  const today = new Date(); today.setHours(0, 0, 0, 0)
  return Math.round((d.getTime() - today.getTime()) / 86_400_000)
}

export function AnalysisSidePanel({ analysis }: { analysis: AnalysisResult }) {
  const t      = useTranslations('analysis.side')
  const locale = useLocale()
  const nf1    = new Intl.NumberFormat(locale, { maximumFractionDigits: 1, minimumFractionDigits: 1 })
  const nf2    = new Intl.NumberFormat(locale, { maximumFractionDigits: 2, minimumFractionDigits: 2 })
  const signed = (v: number) => (v > 0 ? '+' : '') + nf1.format(v) + '%'

  // ── Na tle rynku ──
  const rs   = analysis.relative_strength as
    { index?: string; stock_return_pct?: number; index_return_pct?: number; outperformance_pct?: number } | null
  const beta = analysis.beta_info as { beta?: number; correlation?: number; index?: string } | null
  const hasRs   = rs && typeof rs.stock_return_pct === 'number' && typeof rs.index_return_pct === 'number'
  const hasBeta = beta && typeof beta.beta === 'number'
  const indexName = INDEX_NAMES[rs?.index ?? beta?.index ?? ''] ?? (rs?.index ?? beta?.index ?? '')

  // ── Pozycja ceny ──
  const vwap = analysis.vwap as { vwap?: number; above?: boolean; distance_pct?: number } | null
  const ma   = analysis.ma_crossover as { state?: 'golden' | 'death' } | null
  const hasVwap = vwap && typeof vwap.vwap === 'number' && typeof vwap.distance_pct === 'number'
  const hasMa   = ma && (ma.state === 'golden' || ma.state === 'death')

  // ── Wydarzenia: tylko przyszłe ──
  const cal = analysis.calendar_info
  const events = [
    { key: 'earnings', Icon: BarChart3, color: GREEN,     date: cal?.earnings_date },
    { key: 'exDiv',    Icon: Coins,     color: '#F59E0B', date: cal?.ex_dividend_date },
  ]
    .map(e => ({ ...e, days: e.date ? daysUntil(e.date) : null }))
    .filter((e): e is typeof e & { date: string; days: number } => !!e.date && e.days !== null && e.days >= 0)
    .sort((a, b) => a.days - b.days)

  const when = (n: number) => (n === 0 ? t('events.today') : n === 1 ? t('events.tomorrow') : t('events.inDays', { n }))
  const KNOWN_TYPES = ['stock', 'etf', 'etf_commodity', 'commodity', 'crypto', 'other']
  const typeLabel = KNOWN_TYPES.includes(analysis.asset_type)
    ? t(`types.${analysis.asset_type}`)
    : analysis.asset_type

  return (
    <div className="flex flex-col gap-3">

      {(hasRs || hasBeta) && (
        <Card title={t('market.title')}>
          {hasRs && (() => {
            const s = rs!.stock_return_pct!, i = rs!.index_return_pct!, o = rs!.outperformance_pct ?? s - i
            const max = Math.max(Math.abs(s), Math.abs(i), 1)
            const rows = [
              { label: analysis.ticker, v: s, strong: true },
              { label: indexName,       v: i, strong: false },
            ]
            return (
              <>
                <div className="text-2xs text-muted mb-2">{t('market.period')}</div>
                <div className="space-y-2 mb-3">
                  {rows.map(r => (
                    <div key={r.label} className="flex items-center gap-2">
                      <span className={`text-xs w-16 truncate ${r.strong ? 'font-semibold text-text-hi' : 'text-text-lo'}`}>{r.label}</span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        <div className="h-full rounded-full"
                          style={{ width: `${Math.round(Math.abs(r.v) / max * 100)}%`,
                                   background: r.v >= 0 ? GREEN : RED, opacity: r.strong ? 1 : 0.5 }} />
                      </div>
                      <span className="text-xs font-mono tabular-nums w-14 text-right"
                        style={{ color: r.v >= 0 ? GREEN : RED }}>{signed(r.v)}</span>
                    </div>
                  ))}
                </div>
                <div className="text-xs font-medium"
                  style={{ color: Math.abs(o) < 0.5 ? '#94A3B8' : o > 0 ? GREEN : RED }}>
                  {Math.abs(o) < 0.5 ? t('market.same')
                    : o > 0 ? t('market.better', { pp: nf1.format(Math.abs(o)) })
                            : t('market.worse',  { pp: nf1.format(Math.abs(o)) })}
                </div>
              </>
            )
          })()}

          {hasBeta && (
            <div className={hasRs ? 'mt-3 pt-3 border-t border-border' : ''}>
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-muted">{t('market.beta')}</span>
                <span className="text-sm font-semibold font-mono tabular-nums text-text-hi">{nf2.format(beta!.beta!)}</span>
              </div>
              <p className="text-2xs text-text-lo mt-1 leading-relaxed">
                {beta!.beta! < 0.8 ? t('market.betaLow') : beta!.beta! > 1.2 ? t('market.betaHigh') : t('market.betaMid')}
              </p>
              {typeof beta!.correlation === 'number' && Math.abs(beta!.correlation) < 0.3 && (
                <p className="text-2xs mt-1 leading-relaxed" style={{ color: '#F59E0B' }}>{t('market.weakLink')}</p>
              )}
            </div>
          )}
        </Card>
      )}

      {(hasVwap || hasMa) && (
        <Card title={t('price.title')}>
          <div className="space-y-2.5">
            {hasVwap && (
              <div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-muted">{t('price.vwap')}</span>
                  <span className="text-sm font-semibold font-mono tabular-nums text-text-hi">{nf2.format(vwap!.vwap!)}</span>
                </div>
                <div className="text-2xs mt-0.5 text-right" style={{ color: vwap!.above ? GREEN : RED }}>
                  {t(vwap!.above ? 'price.above' : 'price.below', { pct: nf1.format(Math.abs(vwap!.distance_pct!)) })}
                </div>
              </div>
            )}
            {hasMa && (
              <div className={hasVwap ? 'pt-2.5 border-t border-border' : ''}>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-xs text-muted">{t('price.trend')}</span>
                  <span className="text-xs font-semibold" style={{ color: ma!.state === 'golden' ? GREEN : RED }}>
                    {t(ma!.state === 'golden' ? 'price.bull' : 'price.bear')}
                  </span>
                </div>
                <div className="text-2xs text-text-lo mt-0.5 text-right">
                  {t(ma!.state === 'golden' ? 'price.golden' : 'price.death')}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {events.length > 0 && (
        <Card title={t('events.title')}>
          <div className="space-y-2.5">
            {events.map(e => (
              <div key={e.key} className="flex items-start gap-2.5">
                <e.Icon className="w-4 h-4 shrink-0 mt-0.5" style={{ color: e.color }} />
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-text-hi">{t(`events.${e.key}`)}</div>
                  <div className="flex justify-between gap-2 text-2xs">
                    <span className="text-muted font-mono tabular-nums">{e.date.slice(0, 10)}</span>
                    <span className="text-text-lo">{when(e.days)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title={t('profile.title')}>
        <dl className="space-y-1.5">
          {[
            { k: 'sector',   v: analysis.sector },
            { k: 'industry', v: analysis.industry },
            { k: 'currency', v: analysis.currency },
            { k: 'type',     v: typeLabel },
          ].filter(r => r.v).map(r => (
            <div key={r.k} className="flex justify-between items-baseline gap-3">
              <dt className="text-xs text-muted shrink-0">{t(`profile.${r.k}`)}</dt>
              <dd className="text-xs font-medium text-text-hi text-right break-words min-w-0">{r.v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {analysis.red_flags.length > 0 && (
        <Card title={t('flags.title')}>
          <div className="space-y-1.5">
            {analysis.red_flags.slice(0, 4).map((flag, i) => (
              <div key={i} className="flex items-start gap-2 text-xs rounded-lg px-2.5 py-2"
                style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}>
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />
                <span>{flag}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
