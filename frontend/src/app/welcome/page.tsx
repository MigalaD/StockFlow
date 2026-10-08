'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import {
  ArrowRight, Check, Pause, Play, Plus, LineChart as LineChartIcon, Gauge, ScanLine, Sigma,
} from 'lucide-react'
import { useAuthStore } from '../../store'
import { LanguageSwitcher } from '../../components/shared/LanguageSwitcher'
import { Logo } from '../../components/brand/Logo'

// ── Ograniczenie ruchu ────────────────────────────────────────────────

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// ── Pierścień score (sygnatura hero) ──────────────────────────────────

function HeroScoreRing({ value }: { value: number }) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    if (prefersReducedMotion()) { setShown(value); return }
    const start = Date.now()
    const dur = 1400
    let raf = 0
    const tick = () => {
      const p = Math.min(1, (Date.now() - start) / dur)
      setShown(Math.round(value * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])

  const r = 86
  const circ = 2 * Math.PI * r
  const offset = circ - (shown / 100) * circ
  const color = shown >= 60 ? '#22C55E' : shown >= 40 ? '#F59E0B' : '#EF4444'

  return (
    <div className="relative w-56 h-56">
      <svg viewBox="0 0 200 200" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="100" cy="100" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
        <circle cx="100" cy="100" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-6xl font-bold font-mono tabular-nums" style={{ color }}>{shown}</span>
        <span className="text-2xs text-muted mt-1">Score / 100</span>
      </div>
    </div>
  )
}

// ── Film promocyjny ───────────────────────────────────────────────────
// Odtwarza się tylko wtedy, gdy jest widoczny, i nigdy sam z siebie przy
// włączonym „ogranicz ruch". Wtedy użytkownik uruchamia go przyciskiem.

function PromoFilm() {
  const t = useTranslations('landing.film')
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)
  const [userPaused, setUserPaused] = useState(false)

  useEffect(() => {
    const v = videoRef.current
    if (!v || prefersReducedMotion() || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !userPaused) {
        v.play().then(() => setPlaying(true)).catch(() => setPlaying(false))
      } else {
        v.pause(); setPlaying(false)
      }
    }, { threshold: 0.45 })
    io.observe(v)
    return () => io.disconnect()
  }, [userPaused])

  const toggle = () => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) {
      setUserPaused(false)
      v.play().then(() => setPlaying(true)).catch(() => setPlaying(false))
    } else {
      setUserPaused(true)
      v.pause(); setPlaying(false)
    }
  }

  return (
    <section className="max-w-6xl mx-auto px-6 pt-4 pb-20">
      <div className="relative rounded-2xl overflow-hidden border border-border-hi shadow-lg-dark"
        style={{ background: '#05080F' }}>
        <video
          ref={videoRef}
          className="w-full h-auto block aspect-video"
          src="/landing/promo.mp4"
          poster="/landing/promo-poster.webp"
          muted
          loop
          playsInline
          preload="metadata"
          aria-label={t('label')}
        />
        <button
          type="button"
          onClick={toggle}
          aria-label={playing ? t('pause') : t('play')}
          className="absolute bottom-4 right-4 w-11 h-11 rounded-full flex items-center justify-center
                     border border-border-hi text-text-hi transition-colors hover:text-brand-green"
          style={{ background: 'rgba(8,12,22,0.75)', backdropFilter: 'blur(8px)' }}>
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 translate-x-px" />}
        </button>
      </div>
      <div className="mt-8 grid md:grid-cols-[1fr_auto] gap-4 items-end">
        <h2 className="text-3xl md:text-4xl font-bold text-text-hi tracking-tight text-balance">{t('title')}</h2>
        <p className="text-text-lo max-w-sm md:text-right">{t('lead')}</p>
      </div>
    </section>
  )
}

// ── Eksplorator produktu ──────────────────────────────────────────────

const TABS = [
  { key: 'chart',       Icon: LineChartIcon, src: '/landing/shot-chart.webp',       w: 1400, h: 906 },
  { key: 'score',       Icon: Gauge,         src: '/landing/shot-score.webp',       w: 1100, h: 871 },
  { key: 'scanner',     Icon: ScanLine,      src: '/landing/shot-scanner.webp',     w: 1600, h: 760 },
  { key: 'probability', Icon: Sigma,         src: '/landing/shot-probability.webp', w: 1600, h: 760 },
] as const

function ProductExplorer() {
  const t = useTranslations('landing.explorer')
  const [active, setActive] = useState(0)
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

  const onKey = (e: React.KeyboardEvent, i: number) => {
    const last = TABS.length - 1
    let next = -1
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = i === last ? 0 : i + 1
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft')    next = i === 0 ? last : i - 1
    if (e.key === 'Home') next = 0
    if (e.key === 'End')  next = last
    if (next >= 0) { e.preventDefault(); setActive(next); tabRefs.current[next]?.focus() }
  }

  const tab = TABS[active]
  const k = `tabs.${tab.key}`

  return (
    <section id="features" className="max-w-6xl mx-auto px-6 py-20 scroll-mt-20">
      <div className="max-w-2xl mb-10">
        <h2 className="text-3xl font-bold text-text-hi tracking-tight mb-3 text-balance">{t('title')}</h2>
        <p className="text-text-lo">{t('lead')}</p>
      </div>

      <div className="grid lg:grid-cols-[280px_1fr] gap-6 lg:gap-10">
        <div role="tablist" aria-orientation="vertical"
          className="flex lg:flex-col gap-1 overflow-x-auto -mx-1 px-1 lg:mx-0 lg:px-0">
          {TABS.map((item, i) => {
            const selected = i === active
            return (
              <button
                key={item.key}
                ref={el => { tabRefs.current[i] = el }}
                role="tab"
                id={`tab-${item.key}`}
                aria-selected={selected}
                aria-controls={`panel-${item.key}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(i)}
                onKeyDown={e => onKey(e, i)}
                className="text-left shrink-0 rounded-xl px-4 py-3 transition-colors border-b-2 lg:border-b-0 lg:border-l-2"
                style={{
                  borderColor: selected ? '#22C55E' : 'transparent',
                  background:  selected ? 'rgba(34,197,94,0.07)' : 'transparent',
                }}>
                <span className="flex items-center gap-2.5">
                  <item.Icon className="w-4 h-4 shrink-0" style={{ color: selected ? '#22C55E' : '#64748B' }} />
                  <span className={`font-semibold text-sm whitespace-nowrap ${selected ? 'text-text-hi' : 'text-text-lo'}`}>
                    {t(`tabs.${item.key}.name`)}
                  </span>
                </span>
                <span className="hidden lg:block text-xs text-muted mt-0.5 pl-[26px]">
                  {t(`tabs.${item.key}.short`)}
                </span>
              </button>
            )
          })}
        </div>

        <div role="tabpanel" id={`panel-${tab.key}`} aria-labelledby={`tab-${tab.key}`} key={tab.key}
          className="animate-fade-in min-w-0">
          <div className="rounded-2xl overflow-hidden border border-border bg-surface-1">
            <Image src={tab.src} alt={t(`${k}.alt`)} width={tab.w} height={tab.h}
              sizes="(min-width: 1024px) 800px, 100vw" className="w-full h-auto block"
              priority={active === 0} />
          </div>
          <div className="mt-6 grid md:grid-cols-[1fr_1fr] gap-6">
            <div>
              <h3 className="text-xl font-semibold text-text-hi mb-2 text-balance">{t(`${k}.title`)}</h3>
              <p className="text-sm text-text-lo leading-relaxed">{t(`${k}.body`)}</p>
            </div>
            <ul className="space-y-2.5 md:pt-1">
              {(['p1', 'p2', 'p3'] as const).map(p => (
                <li key={p} className="flex items-start gap-2.5 text-sm text-text-mid">
                  <Check className="w-4 h-4 text-brand-green shrink-0 mt-0.5" />
                  {t(`${k}.${p}`)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Rynki ─────────────────────────────────────────────────────────────
// Liczby pochodzą z list skanera w tickers.py. Przy ich zmianie
// zaktualizuj też te wartości.

const MARKETS = [
  { key: 'usa', n: 71 }, { key: 'gpw', n: 36 }, { key: 'europe', n: 43 },
  { key: 'etf', n: 25 }, { key: 'commodities', n: 11 }, { key: 'crypto', n: 16 },
] as const

function Markets() {
  const t = useTranslations('landing.markets')
  return (
    <section id="markets" className="border-y border-border scroll-mt-20" style={{ background: '#0A0F1B' }}>
      <div className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-text-hi tracking-tight mb-10 text-balance">{t('title')}</h2>
        <dl className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-y-8">
          {MARKETS.map((m, i) => (
            <div key={m.key} className={`flex flex-col-reverse pr-4 ${i > 0 ? 'lg:border-l lg:border-border lg:pl-6' : ''}`}>
              <dt className="text-sm text-text-lo mt-1">{t(m.key)}</dt>
              <dd className="text-4xl font-bold font-mono tabular-nums text-text-hi">{m.n}</dd>
            </div>
          ))}
        </dl>
        <p className="text-sm text-muted mt-10 max-w-xl">{t('lead')}</p>
      </div>
    </section>
  )
}

// ── Pozostałe funkcje ─────────────────────────────────────────────────

const MORE = ['portfolio', 'dividends', 'watchlist', 'calendar', 'backtest', 'compare', 'pdf', 'lang'] as const

function MoreFeatures() {
  const t = useTranslations('landing.more')
  return (
    <section className="max-w-6xl mx-auto px-6 py-20">
      <h2 className="text-2xl font-bold text-text-hi tracking-tight mb-8">{t('title')}</h2>
      <dl className="grid md:grid-cols-2 gap-x-12">
        {MORE.map(key => (
          <div key={key} className="py-4 border-t border-border grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-1 sm:gap-4">
            <dt className="text-sm font-semibold text-text-hi">{t(`items.${key}.t`)}</dt>
            <dd className="text-sm text-text-lo leading-relaxed">{t(`items.${key}.d`)}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

// ── Uczciwie o ograniczeniach ─────────────────────────────────────────

function Honest() {
  const t = useTranslations('landing.honest')
  return (
    <section className="max-w-6xl mx-auto px-6 pb-20">
      <h2 className="text-2xl font-bold text-text-hi tracking-tight mb-8 text-balance">{t('title')}</h2>
      <div className="grid md:grid-cols-3 gap-8 md:gap-0">
        {(['advice', 'data', 'method'] as const).map((key, i) => (
          <div key={key} className={i > 0 ? 'md:border-l md:border-border md:pl-8' : 'md:pr-8'}>
            <h3 className="font-semibold text-text-hi mb-2">{t(`${key}.t`)}</h3>
            <p className="text-sm text-text-lo leading-relaxed">{t(`${key}.d`)}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

// ── Kroki (to faktyczna sekwencja, więc numeracja ma sens) ────────────

function Steps() {
  const t = useTranslations('landing')
  const keys = ['s1', 's2', 's3'] as const
  return (
    <section className="max-w-6xl mx-auto px-6 pb-20">
      <div className="bg-surface-1 border border-border rounded-2xl p-8 md:p-10">
        <h2 className="text-2xl font-bold text-text-hi tracking-tight mb-10 text-balance">{t('stepsTitle')}</h2>
        <ol className="grid md:grid-cols-3 gap-8">
          {keys.map((k, i) => (
            <li key={k}>
              <div className="text-4xl font-bold font-mono mb-3" style={{ color: 'rgba(34,197,94,0.35)' }}>
                {String(i + 1).padStart(2, '0')}
              </div>
              <h3 className="font-semibold text-text-hi mb-2">{t(`steps.${k}.title`)}</h3>
              <p className="text-sm text-text-lo leading-relaxed">{t(`steps.${k}.desc`)}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

// ── FAQ ───────────────────────────────────────────────────────────────
// Natywne <details>: działa bez JS, z klawiatury i z czytnikiem ekranu.

function Faq() {
  const t = useTranslations('landing.faq')
  const items = t.raw('items') as { q: string; a: string }[]
  return (
    <section id="faq" className="max-w-3xl mx-auto px-6 py-20 scroll-mt-20">
      <h2 className="text-3xl font-bold text-text-hi tracking-tight mb-8">{t('title')}</h2>
      <div className="border-t border-border">
        {items.map((item, i) => (
          <details key={i} className="group border-b border-border">
            <summary className="flex items-center justify-between gap-4 py-5 cursor-pointer list-none
                                [&::-webkit-details-marker]:hidden">
              <span className="font-medium text-text-hi">{item.q}</span>
              <Plus className="w-4 h-4 shrink-0 text-muted transition-transform duration-200 group-open:rotate-45" />
            </summary>
            <p className="pb-5 -mt-1 text-sm text-text-lo leading-relaxed max-w-2xl">{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

// ── Strona ────────────────────────────────────────────────────────────

export default function WelcomePage() {
  const router = useRouter()
  const t = useTranslations('landing')
  const { isAuth, _hasHydrated, sessionVerified } = useAuthStore()
  const [barsIn, setBarsIn] = useState(false)

  // Paski w karcie hero rosną chwilę po starcie pierścienia: jeden
  // spójny moment animacji na całej stronie.
  useEffect(() => {
    if (prefersReducedMotion()) { setBarsIn(true); return }
    const id = setTimeout(() => setBarsIn(true), 500)
    return () => clearTimeout(id)
  }, [])

  // Zalogowanych z potwierdzonym tokenem przekieruj do aplikacji.
  useEffect(() => {
    if (_hasHydrated && sessionVerified && isAuth) router.replace('/')
  }, [isAuth, _hasHydrated, sessionVerified, router])

  const bars = [
    { label: t('hero.cardTrend'),    score: 78 },
    { label: t('hero.cardMomentum'), score: 65 },
    { label: t('hero.cardValue'),    score: 71 },
  ]

  return (
    <div className="min-h-screen" style={{ background: '#080C16' }}>

      {/* Nawigacja */}
      <nav className="sticky top-0 z-50 border-b border-border"
        style={{ background: 'rgba(8,12,22,0.8)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <Link href="/welcome" className="flex items-center shrink-0">
            <Logo height={26} priority />
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-text-lo">
            <a href="#features" className="hover:text-text-hi transition-colors">{t('nav.features')}</a>
            <a href="#markets"  className="hover:text-text-hi transition-colors">{t('nav.markets')}</a>
            <a href="#faq"      className="hover:text-text-hi transition-colors">{t('nav.faq')}</a>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <Link href="/login" className="hidden sm:inline text-sm text-text-lo hover:text-text-hi transition-colors">
              {t('nav.login')}
            </Link>
            <Link href="/login" className="btn-primary text-sm">{t('nav.start')}</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-40 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 70% 30%, rgba(34,197,94,0.12), transparent 55%), radial-gradient(ellipse at 20% 70%, rgba(20,184,166,0.10), transparent 50%)' }} />

        <div className="relative max-w-6xl mx-auto px-6 py-20 grid lg:grid-cols-2 gap-12 items-center">
          <div className="animate-slide-up">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-6"
              style={{ background: 'rgba(34,197,94,0.1)', color: '#22C55E', border: '1px solid rgba(34,197,94,0.25)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse-dot" />
              {t('hero.badge')}
            </div>

            <h1 className="text-4xl lg:text-5xl font-bold text-text-hi leading-[1.1] tracking-tight mb-5">
              {t('hero.title1')}<br />
              <span className="text-logo">{t('hero.title2')}</span>
            </h1>

            <p className="text-lg text-text-lo leading-relaxed mb-8 max-w-lg">{t('hero.lead')}</p>

            <div className="flex flex-wrap items-center gap-3 mb-8">
              <Link href="/login" className="btn-primary text-base px-6 py-3">
                {t('hero.ctaPrimary')} <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/login" className="btn-ghost text-base px-5 py-3">{t('hero.ctaSecondary')}</Link>
            </div>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
              {(['trust1', 'trust2', 'trust3'] as const).map(k => (
                <span key={k} className="flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-brand-green" /> {t(`hero.${k}`)}
                </span>
              ))}
            </div>
          </div>

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
                  {bars.map((c, i) => (
                    <div key={c.label} className="flex items-center gap-3">
                      <span className="text-2xs text-muted w-16">{c.label}</span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        <div className="h-full rounded-full"
                          style={{
                            width: barsIn ? `${c.score}%` : '0%',
                            background: '#22C55E',
                            transition: `width 0.9s cubic-bezier(0.16,1,0.3,1) ${i * 120}ms`,
                          }} />
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

      <PromoFilm />
      <ProductExplorer />
      <Markets />
      <MoreFeatures />
      <Honest />
      <Steps />
      <Faq />

      {/* Wezwanie do działania */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="relative overflow-hidden rounded-2xl px-8 py-14 text-center border border-border"
          style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(20,184,166,0.06))' }}>
          <h2 className="text-3xl font-bold text-text-hi tracking-tight mb-3 text-balance">{t('cta.title')}</h2>
          <p className="text-text-lo mb-8 max-w-md mx-auto">{t('cta.lead')}</p>
          <Link href="/login" className="btn-primary text-base px-8 py-3 inline-flex">
            {t('cta.button')} <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Stopka */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo height={20} />
            <span className="text-2xs text-muted">© {new Date().getFullYear()} {t('footer.rights')}</span>
          </div>
          <p className="text-2xs text-muted text-center md:text-right max-w-md leading-relaxed">
            {t('footer.disclaimer')}
          </p>
        </div>
      </footer>
    </div>
  )
}
