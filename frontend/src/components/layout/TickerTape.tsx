'use client'

import { useEffect, useState } from 'react'
import { analysisApi } from '../../lib/api'

interface TickerItem {
  ticker:    string
  price:     number
  change24h: number
  currency:  string
}

// Statyczne dane fallback (gdy API niedostępne)
const FALLBACK: TickerItem[] = [
  { ticker: 'AAPL',    price: 189.42, change24h:  1.24, currency: 'USD' },
  { ticker: 'MSFT',    price: 412.18, change24h:  0.87, currency: 'USD' },
  { ticker: 'NVDA',    price: 875.62, change24h:  2.11, currency: 'USD' },
  { ticker: 'BTC-USD', price: 67420,  change24h:  3.44, currency: 'USD' },
  { ticker: 'ETH-USD', price: 3421,   change24h:  1.92, currency: 'USD' },
  { ticker: 'CDR.WA',  price: 142.30, change24h: -2.10, currency: 'PLN' },
  { ticker: 'PKO.WA',  price: 51.80,  change24h:  0.58, currency: 'PLN' },
  { ticker: 'SAP.DE',  price: 198.44, change24h: -0.32, currency: 'EUR' },
  { ticker: 'GLD',     price: 187.20, change24h:  0.41, currency: 'USD' },
  { ticker: 'META',    price: 486.30, change24h:  1.55, currency: 'USD' },
]

// Formatowanie ceny zależnie od wartości
function formatPrice(price: number, currency: string): string {
  const formatted = price >= 1000
    ? price.toLocaleString('pl-PL', { maximumFractionDigits: 0 })
    : price.toFixed(2)
  return `${formatted} ${currency}`
}

export function TickerTape() {
  const [items, setItems] = useState<TickerItem[]>(FALLBACK)

  // Próba pobrania live danych — bezcicha (nie blokuje UI przy błędzie)
  useEffect(() => {
    const TICKERS_TO_SHOW = ['AAPL', 'MSFT', 'NVDA', 'BTC-USD', 'ETH-USD', 'CDR.WA']
    let cancelled = false

    async function fetchPrices() {
      const results: TickerItem[] = []
      for (const ticker of TICKERS_TO_SHOW) {
        try {
          const data = await analysisApi.analyze(ticker)
          if (!cancelled) {
            results.push({
              ticker:    ticker,
              price:     data.price,
              change24h: 0, // FastAPI nie zwraca change24h — todo: dodać do schematu
              currency:  data.currency,
            })
          }
        } catch {
          // Cicho ignoruj — fallback pozostaje
        }
      }
      if (!cancelled && results.length > 0) {
        setItems(results)
      }
    }

    // Nie blokuj — odśwież w tle po 2s
    const timer = setTimeout(fetchPrices, 2000)
    const interval = setInterval(fetchPrices, 60_000) // co minutę

    return () => {
      cancelled = true
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [])

  // Duplikuj listę dla płynnej animacji (bezszwowe zapętlenie)
  const doubled = [...items, ...items]

  return (
    <div
      className="h-[34px] border-b border-border overflow-hidden flex items-center shrink-0"
      style={{ backgroundColor: '#111827' }}
    >
      <style>{`
        @keyframes ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
        .ticker-inner {
          display: flex;
          animation: ticker 32s linear infinite;
          will-change: transform;
          white-space: nowrap;
        }
        .ticker-inner:hover { animation-play-state: paused; }
      `}</style>

      <div className="ticker-inner">
        {doubled.map((item, i) => {
          const positive = item.change24h >= 0
          const color    = positive ? '#22C55E' : '#EF4444'

          return (
            <div
              key={i}
              className="flex items-center gap-2 px-5 border-r border-border"
              style={{ fontSize: 11 }}
            >
              <span className="text-muted font-medium">{item.ticker}</span>
              <span className="text-white tabular-nums">
                {formatPrice(item.price, item.currency)}
              </span>
              {item.change24h !== 0 && (
                <span style={{ color, fontWeight: 600 }}>
                  {positive ? '▲' : '▼'} {Math.abs(item.change24h).toFixed(2)}%
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
