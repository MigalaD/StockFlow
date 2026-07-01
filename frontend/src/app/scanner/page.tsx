'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { AppShell } from '../../components/layout/AppShell'
import { ScoreBar, scoreColor } from '../../components/ui/ScoreBadge'
import { Button, Tag, EmptyState, Spinner, SectionHeader } from '../../components/ui'
import { scannerApi, type ScanResultItem, type Market } from '../../lib/api'
import { useAuthStore, useScannerStore } from '../../store'
import useSWR from 'swr'

const MARKETS: { value: Market; label: string; count: number }[] = [
  { value: 'usa',    label: 'USA',    count: 53  },
  { value: 'gpw',    label: 'GPW',    count: 24  },
  { value: 'europa', label: 'Europa', count: 33  },
  { value: 'krypto', label: 'Krypto', count: 8   },
  { value: 'all',    label: 'Wszystko', count: 110 },
]

// ── Sector heatmap ────────────────────────────────────────────────────

function SectorHeatmap({ results, mode }: { results: ScanResultItem[]; mode: 'dt' | 'st' }) {
  const sectors = results.reduce<Record<string, { scores: number[]; count: number }>>((acc, r) => {
    if (!r.sector) return acc
    const score = mode === 'st' && r.score_st != null ? r.score_st : r.score
    if (!acc[r.sector]) acc[r.sector] = { scores: [], count: 0 }
    acc[r.sector].scores.push(score)
    acc[r.sector].count++
    return acc
  }, {})

  const averages = Object.entries(sectors)
    .map(([sector, { scores, count }]) => ({
      sector,
      avg:   Math.round(scores.reduce((s, v) => s + v, 0) / scores.length),
      count,
    }))
    .sort((a, b) => b.avg - a.avg)

  if (!averages.length) return (
    <div className="text-xs text-muted text-center py-6">Uruchom skan aby zobaczyć siłę sektorów</div>
  )

  return (
    <div className="space-y-3">
      {averages.map(({ sector, avg, count }) => {
        const color = scoreColor(avg)
        return (
          <div key={sector}>
            <div className="flex justify-between items-center mb-1">
              <div>
                <span className="text-xs text-white font-medium">{sector}</span>
                <span className="text-[10px] text-muted ml-2">{count} sp.</span>
              </div>
              <span className="text-xs font-bold tabular-nums" style={{ color }}>{avg}</span>
            </div>
            <div className="h-2 rounded-full bg-surface-1 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${avg}%`, background: `linear-gradient(90deg, ${color}, ${color}99)` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Distribution chart ────────────────────────────────────────────────

function ScoreDistribution({ results }: { results: ScanResultItem[] }) {
  const buckets = [
    { label: '0–20',  min: 0,  max: 20,  color: '#EF4444' },
    { label: '20–40', min: 20, max: 40,  color: '#F97316' },
    { label: '40–60', min: 40, max: 60,  color: '#F59E0B' },
    { label: '60–80', min: 60, max: 80,  color: '#84CC16' },
    { label: '80–100',min: 80, max: 100, color: '#22C55E' },
  ]

  const counts = buckets.map(b => ({
    ...b,
    count: results.filter(r => r.score >= b.min && r.score < b.max).length,
  }))

  const max = Math.max(...counts.map(c => c.count), 1)

  return (
    <div>
      <div className="text-[10px] text-muted uppercase tracking-widest mb-3">Rozkład score</div>
      <div className="space-y-1.5">
        {counts.map(b => (
          <div key={b.label} className="flex items-center gap-2">
            <span className="text-[10px] text-muted w-12 tabular-nums">{b.label}</span>
            <div className="flex-1 h-4 bg-surface-1 rounded overflow-hidden">
              <div
                className="h-full rounded transition-all duration-500"
                style={{ width: `${(b.count / max) * 100}%`, background: b.color }}
              />
            </div>
            <span className="text-xs tabular-nums font-medium w-6 text-right"
              style={{ color: b.color }}>{b.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Scanner page ──────────────────────────────────────────────────────

type SortCol = 'score' | 'score_st' | 'ticker' | 'price'

export default function ScannerPage() {
  const { isAuth } = useAuthStore()
  const { mode, market, setMode, setMarket } = useScannerStore()

  const [scanning,  setScanning]  = useState(false)
  const [progress,  setProgress]  = useState(0)
  const [current,   setCurrent]   = useState('')
  const [scanDone,  setScanDone]  = useState(0)
  const [scanTotal, setScanTotal] = useState(0)
  const [sortCol,   setSortCol]   = useState<SortCol>('score')
  const [sortDir,   setSortDir]   = useState<'asc' | 'desc'>('desc')
  const [filterQ,   setFilterQ]   = useState('')
  const [scanError, setScanError] = useState('')
  const pollRef = useRef<NodeJS.Timeout>()

  const { data: scan, mutate } = useSWR('scan-results', scannerApi.getResults)

  async function startScan() {
    if (!isAuth) return
    setScanning(true); setProgress(0); setCurrent(''); setScanError('')
    setScanDone(0); setScanTotal(0)
    try {
      await scannerApi.startScan(market as Market)
      pollRef.current = setInterval(async () => {
        try {
          const status = await scannerApi.getStatus()
          setProgress(status.percent)
          setCurrent(status.current)
          setScanDone(status.total ? Math.round(status.percent / 100 * status.total) : 0)
          setScanTotal(status.total)
          if (!status.running) {
            clearInterval(pollRef.current)
            setScanning(false)
            await mutate()
          }
        } catch {
          clearInterval(pollRef.current)
          setScanning(false)
          setScanError('Utracono połączenie podczas skanowania.')
        }
      }, 1500)
    } catch (err: any) {
      setScanning(false)
      if (err?.status === 401) {
        setScanError('Sesja wygasła — zaloguj się ponownie, żeby uruchomić skan.')
      } else {
        setScanError(err?.detail ?? 'Nie udało się uruchomić skanu. Spróbuj ponownie.')
      }
    }
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  function toggleSort(col: SortCol) {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const SortIcon = ({ col }: { col: SortCol }) => (
    <span className="ml-1 opacity-50">{sortCol === col ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span>
  )

  // Filter + sort
  const allResults = scan?.results ?? []
  const filtered = filterQ
    ? allResults.filter(r =>
        r.ticker.includes(filterQ.toUpperCase()) ||
        (r.name ?? '').toLowerCase().includes(filterQ.toLowerCase()) ||
        (r.sector ?? '').toLowerCase().includes(filterQ.toLowerCase())
      )
    : allResults

  const sorted = [...filtered].sort((a, b) => {
    let av: number | string, bv: number | string
    if (sortCol === 'ticker') {
      av = a.ticker; bv = b.ticker
      return sortDir === 'asc' ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    }
    if (sortCol === 'price') { av = a.price ?? 0; bv = b.price ?? 0 }
    else if (sortCol === 'score_st') { av = a.score_st ?? 0; bv = b.score_st ?? 0 }
    else { av = a.score; bv = b.score }
    return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const Th = ({ col, children }: { col: SortCol; children: React.ReactNode }) => (
    <th
      onClick={() => toggleSort(col)}
      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border cursor-pointer hover:text-white transition-colors select-none"
      style={{ background: sortCol === col ? 'rgba(34,197,94,0.05)' : '#0B1120' }}
    >
      {children}<SortIcon col={col} />
    </th>
  )

  return (
    <AppShell>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <h1 className="text-xl font-bold mr-1">🔍 Skaner rynku</h1>

        {/* Mode */}
        <div className="flex bg-surface-2 rounded-lg p-0.5 border border-border">
          {(['dt','st'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)}
              className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
              style={{
                background: mode === m ? 'rgba(34,197,94,0.2)' : 'transparent',
                color:      mode === m ? '#22C55E' : '#64748B',
                border:     mode === m ? '1px solid rgba(34,197,94,0.4)' : '1px solid transparent',
              }}>
              {m === 'dt' ? '📈 Długoterminowy' : '⚡ Swing (ST)'}
            </button>
          ))}
        </div>

        {/* Market */}
        <div className="flex gap-1.5 flex-wrap">
          {MARKETS.map(m => (
            <button key={m.value} onClick={() => setMarket(m.value)}
              className="px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border"
              style={{
                background:  market === m.value ? 'rgba(59,130,246,0.2)' : '#111827',
                color:       market === m.value ? '#3B82F6' : '#64748B',
                borderColor: market === m.value ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
              }}>
              {m.label} <span className="opacity-50">({m.count})</span>
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {scan?.scanned_at && (
            <span className="text-xs text-muted hidden md:block">
              Skan: {scan.scanned_at.slice(0,16).replace('T',' ')}
            </span>
          )}
          <Button onClick={startScan} loading={scanning} disabled={!isAuth || scanning} size="sm">
            {scanning ? `${current || 'Skanowanie'}… ${progress}%` : '▶ Uruchom skan'}
          </Button>
          {!isAuth && (
            <Link href="/login"><Button variant="secondary" size="sm">Zaloguj</Button></Link>
          )}
        </div>
      </div>

      {/* Progress */}
      {scanning && (
        <div className="mb-4 bg-surface-1 border border-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse-dot" />
              <span className="font-semibold text-text-hi">Skanowanie w toku…</span>
            </div>
            <span className="text-xs font-mono text-muted tabular-nums">
              {scanTotal > 0 ? `${scanDone} / ${scanTotal}` : '…'}
              {progress > 0 && ` · ${Math.round(progress)}%`}
            </span>
          </div>
          <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
            <div className="h-full bg-brand-green rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }} />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-muted">
              {current ? `Analizuję: ${current}` : 'Przygotowuję dane…'}
            </span>
            <span className="text-2xs text-muted">
              {progress < 100 && 'To może potrwać do ~minuty — analizujemy każdy instrument osobno.'}
            </span>
          </div>
        </div>
      )}

      {/* Scan error */}
      {scanError && (
        <div className="mb-4 flex items-center justify-between text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <span>⚠ {scanError}</span>
          {scanError.includes('Sesja wygasła') && (
            <Link href="/login">
              <Button size="sm" variant="secondary">Zaloguj ponownie</Button>
            </Link>
          )}
        </div>
      )}

      {/* Filter */}
      {allResults.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <input
            value={filterQ}
            onChange={e => setFilterQ(e.target.value)}
            placeholder="Filtruj po tickerze, nazwie lub sektorze…"
            className="input max-w-sm text-sm"
          />
          {filterQ && (
            <button onClick={() => setFilterQ('')}
              className="text-xs text-muted hover:text-white transition-colors">
              ✕ Wyczyść
            </button>
          )}
          <span className="text-xs text-muted">{sorted.length} / {allResults.length}</span>
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_260px] gap-4">

        {/* Table */}
        <div>
          {!scan || allResults.length === 0 ? (
            <div className="bg-surface-1 border border-border rounded-xl2">
              <EmptyState icon="🔍" title="Brak wyników skanu"
                desc="Uruchom skan aby zobaczyć ranking instrumentów"
                action={isAuth
                  ? <Button onClick={startScan} loading={scanning}>Uruchom skan</Button>
                  : <Link href="/login"><Button variant="secondary">Zaloguj się</Button></Link>
                } />
            </div>
          ) : (
            <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border w-8"
                      style={{ background: '#0B1120' }}>#</th>
                    <Th col="ticker">Ticker</Th>
                    <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border hidden md:table-cell"
                      style={{ background: '#0B1120' }}>Sektor</th>
                    <Th col="price">Cena</Th>
                    <Th col="score">
                      <span style={{ color: mode === 'dt' ? '#22C55E' : '#94A3B8' }}>DT</span>
                    </Th>
                    <Th col="score_st">
                      <span style={{ color: mode === 'st' ? '#22C55E' : '#94A3B8' }}>⚡ ST</span>
                    </Th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r, i) => (
                    <tr key={r.ticker}
                      className="border-b border-border hover:bg-surface-2/40 transition-colors"
                      style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(11,17,32,0.3)' }}>
                      <td className="px-3 py-2.5 text-xs text-muted tabular-nums">{i + 1}</td>
                      <td className="px-3 py-2.5">
                        <Link href={`/analysis?ticker=${r.ticker}`}>
                          <span className="font-bold text-sm text-white hover:text-brand-green transition-colors">
                            {r.ticker}
                          </span>
                        </Link>
                        {r.name && <div className="text-xs text-muted truncate max-w-[120px]">{r.name}</div>}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell">
                        {r.sector && <Tag>{r.sector}</Tag>}
                      </td>
                      <td className="px-3 py-2.5 text-sm tabular-nums text-white">
                        {r.price != null ? r.price.toFixed(2) : '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        <ScoreBar score={r.score}
                          width={mode === 'dt' ? 'w-16' : 'w-12'} />
                      </td>
                      <td className="px-3 py-2.5">
                        {r.score_st != null
                          ? <ScoreBar score={r.score_st} width={mode === 'st' ? 'w-16' : 'w-12'} />
                          : <span className="text-muted text-xs">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-2.5 text-xs text-muted border-t border-border">
                {sorted.length} instrumentów · Kliknij nagłówek kolumny aby sortować ·
                Wysoki score ≠ sygnał kupna
              </div>
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          <div className="bg-surface-1 border border-border rounded-xl2 overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <span className="font-semibold text-sm text-white">Siła sektorów</span>
            </div>
            <div className="p-4">
              <SectorHeatmap results={sorted} mode={mode} />
            </div>
          </div>

          {sorted.length > 0 && (
            <div className="bg-surface-1 border border-border rounded-xl2 p-4">
              <ScoreDistribution results={sorted} />
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
