'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  TrendingUp, BarChart3, ScanLine, FlaskConical, Bell,
  ArrowRight, Check, LineChart as LineChartIcon,
} from 'lucide-react'
import { useAuthStore } from '../../store'

// ── Mini animated score ring (hero signature) ─────────────────────────

function HeroScoreRing({ value }: { value: number }) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const start = Date.now()
    const dur = 1400
    const tick = () => {
      const t = Math.min(1, (Date.now() - start) / dur)
      const eased = 1 - Math.pow(1 - t, 3)
      setShown(Math.round(value * eased))
      if (t < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [value])

  const r = 86
  const circ = 2 * Math.PI * r
  const offset = circ - (shown / 100) * circ
  const color = shown >= 60 ? '#22C55E' : shown >= 40 ? '#F59E0B' : '#EF4444'

  return (
    <div className="relative w-56 h-56">
      <svg viewBox="0 0 200 200" className="w-full h-full -rotate-90">
        <circle cx="100" cy="100" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
        <circle cx="100" cy="100" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-6xl font-bold font-mono tabular-nums" style={{ color }}>{shown}</span>
        <span className="text-2xs uppercase tracking-[0.2em] text-muted mt-1">Score / 100</span>
      </div>
    </div>
  )
}

const FEATURES = [
  { icon: BarChart3,   title: 'Score 0–100',     desc: 'Każdy instrument oceniony przez kilkanaście wskaźników technicznych i fundamentalnych — jeden czytelny wynik.' },
  { icon: LineChartIcon, title: 'Wykresy pro',    desc: 'Świece, Bollinger, średnie kroczące, zoom i dane live. To czego potrzebujesz do analizy w jednym miejscu.' },
  { icon: ScanLine,       title: 'Skaner rynku',    desc: 'Przeskanuj USA, GPW, Europę i krypto. Ranking instrumentów po sile w sekundy.' },
  { icon: FlaskConical, title: 'Backtest',        desc: 'Sprawdź jak strategia score zachowywała się historycznie — equity curve, Sharpe, walk-forward.' },
  { icon: TrendingUp,  title: 'Scenariusze',     desc: 'Symulacja Monte Carlo pokazuje zakres możliwych ścieżek ceny, nie jedną fałszywą prognozę.' },
  { icon: Bell,        title: 'Alerty Telegram', desc: 'Dostań powiadomienie gdy score instrumentu przekroczy ustawiony przez Ciebie próg.' },
]

const STEPS = [
  { n: '01', title: 'Wpisz symbol',   desc: 'AAPL, CD Projekt, Bitcoin — cokolwiek chcesz przeanalizować.' },
  { n: '02', title: 'Zobacz score',   desc: 'Natychmiastowa ocena z rozbiciem na składowe i sygnały.' },
  { n: '03', title: 'Podejmij decyzję', desc: 'Pełen obraz: wykres, scenariusze, strategie — wszystko po polsku.' },
]

export default function WelcomePage() {
  const router = useRouter()
  const { isAuth, _hasHydrated } = useAuthStore()

  // Zalogowanych przekieruj prosto do aplikacji
  useEffect(() => {
    if (_hasHydrated && isAuth) router.replace('/')
  }, [isAuth, _hasHydrated, router])

  return (
    <div className="min-h-screen" style={{ background: '#080C16' }}>

      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-border"
        style={{ background: 'rgba(8,12,22,0.8)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #22C55E, #14B8A6)' }}>
              <TrendingUp className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-bold text-lg text-logo">StockFlow</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-text-lo hover:text-text-hi transition-colors">
              Zaloguj się
            </Link>
            <Link href="/login" className="btn-primary text-sm">
              Zacznij za darmo
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-40 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 70% 30%, rgba(34,197,94,0.12), transparent 55%), radial-gradient(ellipse at 20% 70%, rgba(20,184,166,0.10), transparent 50%)' }} />

        <div className="relative max-w-6xl mx-auto px-6 py-20 grid lg:grid-cols-2 gap-12 items-center">
          <div className="animate-slide-up">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-2xs font-semibold uppercase tracking-wider mb-6"
              style={{ background: 'rgba(34,197,94,0.1)', color: '#22C55E', border: '1px solid rgba(34,197,94,0.25)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse-dot" />
              Analityka rynkowa po polsku
            </div>

            <h1 className="text-5xl font-bold text-text-hi leading-[1.1] tracking-tight mb-5">
              Analizuj rynki<br/>
              <span className="text-logo">bez chaosu danych.</span>
            </h1>

            <p className="text-lg text-text-lo leading-relaxed mb-8 max-w-lg">
              StockFlow zamienia dziesiątki wskaźników w jeden czytelny wynik.
              Akcje, ETF-y, kryptowaluty i surowce — przeanalizowane w sekundy,
              wyjaśnione prostym językiem.
            </p>

            <div className="flex items-center gap-3 mb-8">
              <Link href="/login" className="btn-primary text-base px-6 py-3">
                Rozpocznij analizę <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/login" className="btn-ghost text-base px-5 py-3">
                Mam już konto
              </Link>
            </div>

            <div className="flex items-center gap-5 text-2xs text-muted">
              {['Bez karty', 'Bez reklam', 'Dane szyfrowane'].map(item => (
                <span key={item} className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-brand-green" /> {item}
                </span>
              ))}
            </div>
          </div>

          {/* Hero visual — signature score ring */}
          <div className="flex justify-center lg:justify-end animate-fade-in">
            <div className="relative">
              <div className="absolute -inset-8 rounded-full opacity-20 blur-3xl"
                style={{ background: 'radial-gradient(circle, #22C55E, transparent 70%)' }} />
              <div className="relative bg-surface-1 border border-border rounded-2xl p-8 shadow-lg-dark">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="font-bold text-text-hi font-mono">AAPL</div>
                    <div className="text-2xs text-muted">Apple Inc.</div>
                  </div>
                  <span className="flex items-center gap-1 font-mono font-semibold text-sm px-2 py-0.5 rounded-md"
                    style={{ color: '#22C55E', background: 'rgba(34,197,94,0.12)' }}>
                    ▲ +1.24%
                  </span>
                </div>
                <div className="flex justify-center mb-6">
                  <HeroScoreRing value={72} />
                </div>
                <div className="space-y-2">
                  {[
                    { label: 'Trend', score: 78 },
                    { label: 'Momentum', score: 65 },
                    { label: 'Wartość', score: 71 },
                  ].map(c => (
                    <div key={c.label} className="flex items-center gap-3">
                      <span className="text-2xs text-muted w-16">{c.label}</span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        <div className="h-full rounded-full" style={{ width: `${c.score}%`, background: '#22C55E' }} />
                      </div>
                      <span className="text-2xs font-mono font-bold w-6 text-right" style={{ color: '#22C55E' }}>{c.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-text-hi tracking-tight mb-3">
            Wszystko czego potrzebujesz do analizy
          </h2>
          <p className="text-text-lo max-w-xl mx-auto">
            Profesjonalne narzędzia, które wcześniej wymagały kilku osobnych platform — teraz w jednym miejscu.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title}
              className="bg-surface-1 border border-border rounded-xl2 p-6 hover:bg-surface-2 hover:border-border-hi transition-all">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
                style={{ background: 'rgba(34,197,94,0.1)' }}>
                <Icon className="w-5 h-5 text-brand-green" />
              </div>
              <h3 className="font-semibold text-text-hi mb-2">{title}</h3>
              <p className="text-sm text-text-lo leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="bg-surface-1 border border-border rounded-2xl p-10">
          <h2 className="text-2xl font-bold text-text-hi tracking-tight mb-10 text-center">
            Od symbolu do decyzji w trzech krokach
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map((s, i) => (
              <div key={s.n} className="relative">
                <div className="text-5xl font-bold font-mono mb-3" style={{ color: 'rgba(34,197,94,0.25)' }}>
                  {s.n}
                </div>
                <h3 className="font-semibold text-text-hi mb-2">{s.title}</h3>
                <p className="text-sm text-text-lo leading-relaxed">{s.desc}</p>
                {i < STEPS.length - 1 && (
                  <ArrowRight className="hidden md:block absolute top-6 -right-4 w-5 h-5 text-muted" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="relative overflow-hidden rounded-2xl p-12 text-center border border-border"
          style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(20,184,166,0.06))' }}>
          <div className="absolute inset-0 opacity-30 pointer-events-none"
            style={{ background: 'radial-gradient(circle at 50% 0%, rgba(34,197,94,0.15), transparent 60%)' }} />
          <div className="relative">
            <h2 className="text-3xl font-bold text-text-hi tracking-tight mb-3">
              Zacznij analizować już dziś
            </h2>
            <p className="text-text-lo mb-8 max-w-md mx-auto">
              Bezpłatne konto. Bez karty kredytowej. Pierwszą analizę zrobisz w mniej niż minutę.
            </p>
            <Link href="/login" className="btn-primary text-base px-8 py-3 inline-flex">
              Utwórz darmowe konto <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border mt-8">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-green" />
            <span className="font-semibold text-text-mid text-sm">StockFlow</span>
            <span className="text-2xs text-muted ml-2">© 2026</span>
          </div>
          <p className="text-2xs text-muted text-center md:text-right max-w-md">
            StockFlow jest narzędziem edukacyjnym i nie stanowi porady inwestycyjnej.
            Inwestycje wiążą się z ryzykiem utraty kapitału.
          </p>
        </div>
      </footer>
    </div>
  )
}
