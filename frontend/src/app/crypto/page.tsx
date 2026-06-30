'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBadge, ScoreBar, scoreColor } from '../../components/ui/ScoreBadge'
import { Card, SectionHeader, Button, Spinner, EmptyState, Tag, Price } from '../../components/ui'
import { analysisApi } from '../../lib/api'

const CRYPTO_TICKERS = [
  { ticker:'BTC-USD', name:'Bitcoin',   icon:'₿'  },
  { ticker:'ETH-USD', name:'Ethereum',  icon:'Ξ'  },
  { ticker:'BNB-USD', name:'BNB',       icon:'🔶' },
  { ticker:'SOL-USD', name:'Solana',    icon:'◎'  },
  { ticker:'XRP-USD', name:'XRP',       icon:'✕'  },
  { ticker:'ADA-USD', name:'Cardano',   icon:'₳'  },
  { ticker:'AVAX-USD',name:'Avalanche', icon:'🔺' },
  { ticker:'DOT-USD', name:'Polkadot',  icon:'⬤'  },
]

function CryptoCard({ ticker, name, icon }: { ticker: string; name: string; icon: string }) {
  const { data, isLoading } = useSWR(
    `crypto-${ticker}`,
    () => analysisApi.analyze(ticker),
    { refreshInterval: 60_000 },
  )

  if (isLoading) return (
    <div className="skeleton rounded-xl2 h-[140px]" />
  )
  if (!data) return null

  const color = scoreColor(data.total_score)

  return (
    <Link href={`/analysis?ticker=${ticker}`}>
      <div
        className="bg-surface-1 border border-border rounded-xl2 p-4 hover:bg-surface-2 hover:border-border-hi transition-all cursor-pointer"
        style={{ borderTop: `2px solid ${color}` }}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{icon}</span>
            <div>
              <div className="font-bold text-text-hi text-sm">{name}</div>
              <div className="text-2xs text-muted font-mono">{ticker}</div>
            </div>
          </div>
          <ScoreBadge score={data.total_score} size="sm" />
        </div>

        <div className="mb-2">
          <Price value={data.price} currency={data.currency}
            decimals={data.price >= 1000 ? 0 : 2}
            className="text-lg font-bold text-text-hi" />
        </div>

        <div className="flex items-center justify-between">
          <ScoreBar score={data.total_score} width="w-20" />
          {data.score_st != null && (
            <div className="flex items-center gap-1">
              <span className="text-2xs text-muted">⚡ ST</span>
              <span className="text-xs font-bold font-mono tabular-nums" style={{ color: scoreColor(data.score_st) }}>
                {Math.round(data.score_st)}
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}

function DominanceWidget() {
  // Uproszczone — BTC dominance z analizy BTC
  const { data } = useSWR('btc-for-dom', () => analysisApi.analyze('BTC-USD'))

  const btcDom = (data?.relative_strength as any)?.btc_dominance
  if (!btcDom) return null

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4">
      <div className="text-2xs text-muted uppercase tracking-widest mb-1">BTC Dominacja</div>
      <div className="text-2xl font-bold font-mono tabular-nums" style={{ color: '#F59E0B' }}>
        {btcDom.toFixed(1)}%
      </div>
      <div className="text-xs text-muted mt-1">
        {btcDom > 55 ? 'Dominacja BTC — altcoiny słabsze' :
         btcDom > 45 ? 'Zrównoważony rynek' :
         'Sezon altcoinów'}
      </div>
    </div>
  )
}

export default function CryptoPage() {
  const t = useTranslations('crypto')

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold">{t('title')}</h1>
        <Tag className="text-brand-teal border-brand-teal/40 bg-brand-teal/10">
          ₿ {t('binanceLive')}
        </Tag>
      </div>

      {/* Disclaimer */}
      <details className="mb-5">
        <summary className="text-xs text-muted cursor-pointer hover:text-white transition-colors">
          ℹ️ O scoringu krypto — kliknij aby rozwinąć
        </summary>
        <div className="mt-2 text-sm text-muted bg-surface border border-border rounded-lg p-3 leading-relaxed">
          Score krypto uwzględnia analizę techniczną (trend, RSI, MACD, momentum) skalowaną pod
          realia rynku krypto oraz siłę względem Bitcoina. Kryptowaluty nie mają fundamentów
          spółki (P/E, dywidendy). <strong style={{ color:'#F59E0B' }}>⚠ {t('disclaimer')}</strong>
        </div>
      </details>

      <div className="grid grid-cols-[1fr_200px] gap-5">
        <div>
          <SectionHeader title="Kryptowaluty" icon="₿" desc="Score techniczny · dane live z Binance" />
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {CRYPTO_TICKERS.map(c => (
              <CryptoCard key={c.ticker} {...c} />
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <DominanceWidget />
          <div className="bg-surface-1 border border-border rounded-xl2 p-4">
            <div className="text-2xs text-muted uppercase tracking-widest mb-3">Skróty analizy</div>
            {CRYPTO_TICKERS.slice(0, 4).map(c => (
              <Link key={c.ticker} href={`/analysis?ticker=${c.ticker}`}>
                <div className="flex items-center gap-2 py-2 border-b border-border hover:text-brand-green transition-colors">
                  <span>{c.icon}</span>
                  <span className="text-sm text-text-mid flex-1 font-mono">{c.ticker}</span>
                  <span className="text-xs text-muted">→</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
