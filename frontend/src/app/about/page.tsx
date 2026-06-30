'use client'

import { AppShell } from '../../components/layout/AppShell'
import { SectionHeader, Tag } from '../../components/ui'
import Link from 'next/link'

const FEATURES = [
  { icon:'📈', title:'Score DT', desc:'Wynik długoterminowy 0–100 z 8–12 wskaźników technicznych i fundamentalnych.' },
  { icon:'⚡', title:'Score ST', desc:'Wynik krótkoterminowy (swing) z RSI-7, Stochastik, OBV, VWAP.' },
  { icon:'🔍', title:'Skaner',   desc:'Automatyczny skan USA, GPW, Europy i kryptowalut z rankingiem.' },
  { icon:'⭐', title:'Watchlista', desc:'Obserwuj instrumenty i otrzymuj alerty gdy score zmienia się znacząco.' },
  { icon:'💼', title:'Portfolio', desc:'Śledzenie P&L, alokacja sektorowa, macierz korelacji.' },
  { icon:'🧪', title:'Backtest', desc:'Test strategii score score na danych historycznych.' },
]

const STACK = [
  ['Python 3.11', 'Logika scoringu, moduły analityczne'],
  ['FastAPI',     'REST API z dokumentacją auto-Swagger'],
  ['Next.js 14',  'Frontend z App Router i SSR'],
  ['Supabase',    'PostgreSQL + auth + realtime'],
  ['Vercel',      'Hosting frontendu (edge network)'],
  ['Railway',     'Hosting backendu FastAPI'],
  ['Lightweight Charts', 'Wykresy finansowe TradingView'],
  ['Yahoo Finance', 'Dane historyczne (darmowe)'],
  ['Binance API', 'Ceny krypto live (bez klucza)'],
]

export default function AboutPage() {
  return (
    <AppShell>
      {/* Hero */}
      <div className="mb-8 text-center py-8">
        <div className="text-4xl font-bold tracking-tight mb-2">
          <span style={{ color:'#22C55E' }}>Stock</span>
          <span style={{ color:'#14B8A6' }}>Flow</span>
        </div>
        <div className="text-muted text-sm mb-4">
          Narzędzie edukacyjne do analizy rynkowej · v1.2
        </div>
        <div className="flex justify-center gap-2 flex-wrap">
          {['Edukacyjny','Bez reklam','Open-core','PL/EN'].map(tag => (
            <Tag key={tag} className="text-brand-green border-brand-green/40 bg-brand-green/10 text-xs">
              {tag}
            </Tag>
          ))}
        </div>
      </div>

      <div className="max-w-3xl mx-auto space-y-6">

        {/* Disclaimer */}
        <div
          className="rounded-xl2 p-4 text-sm leading-relaxed"
          style={{ background:'rgba(239,68,68,0.08)', border:'1px solid rgba(239,68,68,0.2)', color:'#FCA5A5' }}
        >
          <strong>⚠ Ważne:</strong> StockFlow jest narzędziem <strong>edukacyjnym</strong>.
          Wyniki analizy, score i sygnały <strong>nie stanowią porady inwestycyjnej</strong> w
          rozumieniu prawa. Inwestycje na rynku kapitałowym wiążą się z ryzykiem utraty kapitału.
          Przed podjęciem decyzji inwestycyjnych skonsultuj się z licencjonowanym doradcą
          finansowym.
        </div>

        {/* Features */}
        <div>
          <SectionHeader title="Funkcje" icon="✨" />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {FEATURES.map(f => (
              <div key={f.title} className="bg-surface-1 border border-border rounded-xl2 p-4 hover:bg-surface-2 transition-colors">
                <div className="text-2xl mb-2">{f.icon}</div>
                <div className="font-semibold text-sm text-text-hi mb-1">{f.title}</div>
                <div className="text-xs text-muted leading-relaxed">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Score explanation */}
        <div>
          <SectionHeader title="Jak działa Score?" icon="🧮" />
          <div className="bg-surface-1 border border-border rounded-xl2 p-5 space-y-3 text-sm text-muted leading-relaxed">
            <p>
              Score DT (Długoterminowy) to ważona suma punktów z 8–12 wskaźników technicznych
              i fundamentalnych. Każdy wskaźnik dostaje 0–100 punktów zależnie od swojego stanu.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { range:'60–100', label:'Pozytywny',  color:'#22C55E', desc:'Większość wskaźników sprzyja' },
                { range:'40–59',  label:'Neutralny',  color:'#F59E0B', desc:'Sygnały mieszane' },
                { range:'0–39',   label:'Negatywny',  color:'#EF4444', desc:'Większość wskaźników negatywna' },
              ].map(s => (
                <div
                  key={s.range}
                  className="text-center rounded-lg p-3"
                  style={{ background: s.color + '14', border: `1px solid ${s.color}30` }}
                >
                  <div className="font-bold text-lg" style={{ color: s.color }}>{s.range}</div>
                  <div className="font-semibold text-xs text-white mt-0.5">{s.label}</div>
                  <div className="text-[10px] text-muted mt-1">{s.desc}</div>
                </div>
              ))}
            </div>
            <p className="text-xs">
              Score ST (Krótkoterminowy/Swing) używa innych wskaźników (RSI-7, Stochastik, OBV,
              VWAP) z horyzontem kilku dni do kilku tygodni.
            </p>
          </div>
        </div>

        {/* Tech stack */}
        <div>
          <SectionHeader title="Stack technologiczny" icon="⚙️" />
          <div className="bg-surface border border-border rounded-xl2 overflow-hidden">
            {STACK.map(([tech, desc], i) => (
              <div
                key={tech}
                className="flex items-center justify-between px-4 py-3 border-b border-border last:border-0"
              >
                <span className="text-sm font-semibold text-white">{tech}</span>
                <span className="text-xs text-muted">{desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Data sources */}
        <div>
          <SectionHeader title="Źródła danych" icon="📡" />
          <div className="bg-surface border border-border rounded-xl2 p-4 text-sm text-muted space-y-2">
            <p>• <strong className="text-white">Yahoo Finance</strong> — historia cen, dane fundamentalne (~15 min opóźnienia)</p>
            <p>• <strong className="text-white">Binance API</strong> — live ceny kryptowalut (bez opóźnienia, bez klucza API)</p>
            <p>• <strong className="text-white">CoinGecko</strong> — BTC dominacja rynku</p>
            <p className="text-xs pt-2">
              Dane są dostarczane "as is". StockFlow nie ponosi odpowiedzialności za opóźnienia,
              błędy ani przerwy w dostawie danych przez zewnętrznych dostawców.
            </p>
          </div>
        </div>

        {/* Links */}
        <div className="flex flex-wrap gap-3 pt-2">
          <a
            href="https://github.com/migalad/stockflow"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-brand-green hover:underline"
          >
            GitHub →
          </a>
          <Link href="/settings" className="text-sm text-muted hover:text-white transition-colors">
            Ustawienia →
          </Link>
        </div>

        <p className="text-center text-xs text-muted pb-4">
          © 2026 Damian Migała / StockFlow · Wszelkie prawa zastrzeżone
        </p>
      </div>
    </AppShell>
  )
}
