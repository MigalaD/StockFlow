'use client'

import { useState, useEffect, useRef } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { AppShell } from '../components/layout/AppShell'
import { ScoreBar, scoreColor } from '../components/ui/ScoreBadge'
import { Card, CardHeader, SectionHeader, Button, Tag, EmptyState, Spinner } from '../components/ui'
import { scannerApi, type ScanResultItem, type Market } from '../lib/api'
import { useAuthStore, useScannerStore } from '../store'

const MARKETS: { value: Market; labelKey: string }[] = [
  { value: 'usa',    labelKey: 'usa'    },
  { value: 'gpw',    labelKey: 'gpw'    },
  { value: 'europa', labelKey: 'europa' },
  { value: 'krypto', labelKey: 'krypto' },
  { value: 'all',    labelKey: 'all'    },
]

// ── Sector heatmap ────────────────────────────────────────────────────

function SectorHeatmap({ results, mode }: { results: ScanResultItem[]; mode: 'dt' | 'st' }) {
  const sectors = results.reduce<Record<string, number[]>>((acc, r) => {
    if (!r.sector) return acc
    const score = mode === 'st' && r.score_st != null ? r.score_st : r.score
    if (!acc[r.sector]) acc[r.sector] = []
    acc[r.sector].push(score)
    return acc
  }, {})

  const averages = Object.entries(sectors)
    .map(([sector, scores]) => ({
      sector,
      avg: scores.reduce((s, v) => s + v, 0) / scores.length,
      count: scores.length,
    }))
    .sort((a, b) => b.avg - a.avg)

  return (
    <div className="space-y-2.5">
      {averages.map(({ sector, avg, count }) => (
        <div key={sector}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-white">{sector}</span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted">{count} sp.</span>
              <span className="text-xs font-bold tabular-nums" style={{ color: scoreColor(avg) }}>
                {avg.toFixed(0)}
              </span>
            </div>
          </div>
          <div className="h-1.5 rounded-full bg-surface overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${avg}%`,
                background: `linear-gradient(90deg, ${scoreColor(avg)}, ${scoreColor(avg)}99)`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Scanner page ──────────────────────────────────────────────────────

export default function ScannerPage() {
  const t = useTranslations('scanner')
  const { isAuth } = useAuthStore()
  const { mode, market, setMode, setMarket } = useScannerStore()

  const [scanning, setScanning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [sortCol,  setSortCol]  = useState<'score' | 'score_st' | 'ticker'>('score')
  const [sortDir,  setSortDir]  = useState<'asc' | 'desc'>('desc')
  const pollRef = useRef<NodeJS.Timeout>()

  const { data: scan, mutate } = useSWR('scan-results', scannerApi.getResults)

  async function startScan() {
    if (!isAuth) return
    setScanning(true)
    setProgress(0)
    try {
      await scannerApi.startScan(market as Market)

      // Poll status
      pollRef.current = setInterval(async () => {
        const status = await scannerApi.getStatus()
        setProgress(status.percent)
        if (!status.running) {
          clearInterval(pollRef.current)
          setScanning(false)
          setProgress(100)
          await mutate()
        }
      }, 1500)
    } catch {
      setScanning(false)
    }
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  // Sort results
  const results = [...(scan?.results ?? [])].sort((a, b) => {
    let aVal: number, bVal: number
    if (sortCol === 'ticker') {
      return sortDir === 'asc'
        ? a.ticker.localeCompare(b.ticker)
        : b.ticker.localeCompare(a.ticker)
    }
    aVal = sortCol === 'score_st' ? (a.score_st ?? 0) : a.score
    bVal = sortCol === 'score_st' ? (b.score_st ?? 0) : b.score
    return sortDir === 'asc' ? aVal - bVal : bVal - aVal
  })

  function toggleSort(col: typeof sortCol) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
      setSortDir('desc')
    }
  }

  const SortIcon = ({ col }: { col: typeof sortCol }) => (
    <span className="ml-1 text-muted">
      {sortCol === col ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}
    </span>
  )

  return (
    <AppShell>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <h1 className="text-xl font-bold mr-2">{t('title')}</h1>

        {/* Mode toggle */}
        <div className="flex bg-surface-hi rounded-lg p-0.5 border border-border">
          {(['dt', 'st'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
              style={{
                background: mode === m ? 'rgba(34,197,94,0.2)' : 'transparent',
                color:      mode === m ? '#22C55E' : '#64748B',
                border:     mode === m ? '1px solid rgba(34,197,94,0.4)' : '1px solid transparent',
              }}
            >
              {m === 'dt' ? '📈 ' + t('mode.dt') : '⚡ ' + t('mode.st')}
            </button>
          ))}
        </div>

        {/* Market selector */}
        <div className="flex gap-1.5 flex-wrap">
          {MARKETS.map(m => (
            <button
              key={m.value}
              onClick={() => setMarket(m.value)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all border"
              style={{
                background:  market === m.value ? 'rgba(59,130,246,0.2)' : '#111827',
                color:       market === m.value ? '#3B82F6' : '#64748B',
                borderColor: market === m.value ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.07)',
              }}
            >
              {t(`market.${m.value}`)}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {scan?.scanned_at && (
            <span className="text-xs text-muted">
              Skan: {scan.scanned_at.slice(0, 16).replace('T', ' ')}
            </span>
          )}
          <Button
            onClick={startScan}
            loading={scanning}
            disabled={!isAuth || scanning}
            size="sm"
          >
            {scanning ? `${t('running')} ${progress}%` : t('run')}
          </Button>
          {!isAuth && (
            <Link href="/login">
              <Button variant="secondary" size="sm">Zaloguj</Button>
            </Link>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {scanning && (
        <div className="mb-4 h-1.5 bg-surface-hi rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-green rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-[1fr_240px] gap-4">

        {/* Results table */}
        <div>
          {!scan || scan.results.length === 0 ? (
            <div className="bg-surface border border-border rounded-xl2">
              <EmptyState
                icon="🔍"
                title={t('results')}
                desc="Uruchom skan aby zobaczyć wyniki"
                action={isAuth
                  ? <Button onClick={startScan} loading={scanning}>{t('run')}</Button>
                  : <Link href="/login"><Button variant="secondary">Zaloguj się</Button></Link>
                }
              />
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-xl2 overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr style={{ backgroundColor: '#0B1120' }}>
                    <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border w-8">
                      #
                    </th>
                    <th
                      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border cursor-pointer hover:text-white"
                      onClick={() => toggleSort('ticker')}
                    >
                      Ticker <SortIcon col="ticker" />
                    </th>
                    <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border hidden md:table-cell">
                      Sektor
                    </th>
                    <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider text-muted font-medium border-b border-border">
                      Cena
                    </th>
                    <th
                      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider font-medium border-b border-border cursor-pointer hover:text-white"
                      style={{ color: mode === 'dt' ? '#22C55E' : '#64748B' }}
                      onClick={() => toggleSort('score')}
                    >
                      DT <SortIcon col="score" />
                    </th>
                    <th
                      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-wider font-medium border-b border-border cursor-pointer hover:text-white"
                      style={{ color: mode === 'st' ? '#22C55E' : '#64748B' }}
                      onClick={() => toggleSort('score_st')}
                    >
                      ⚡ ST <SortIcon col="score_st" />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={r.ticker} className="border-b border-border hover:bg-surface-hi/40">
                      <td className="px-3 py-2.5 text-xs text-muted tabular-nums">{i + 1}</td>
                      <td className="px-3 py-2.5">
                        <Link href={`/analysis?ticker=${r.ticker}`}>
                          <span className="font-bold text-sm text-white hover:text-brand-green transition-colors">
                            {r.ticker}
                          </span>
                        </Link>
                        {r.name && (
                          <div className="text-xs text-muted truncate max-w-[130px]">{r.name}</div>
                        )}
                      </td>
                      <td className="px-3 py-2.5 hidden md:table-cell">
                        {r.sector && <Tag>{r.sector}</Tag>}
                      </td>
                      <td className="px-3 py-2.5 text-sm tabular-nums text-white">
                        {r.price != null ? r.price.toFixed(2) : '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        <ScoreBar
                          score={r.score}
                          width={mode === 'dt' ? 'w-16' : 'w-12'}
                        />
                      </td>
                      <td className="px-3 py-2.5">
                        {r.score_st != null
                          ? <ScoreBar score={r.score_st} width={mode === 'st' ? 'w-16' : 'w-12'} />
                          : <span className="text-muted text-xs">—</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-2.5 text-xs text-muted border-t border-border">
                {results.length} instrumentów · {t('disclaimer')}
              </div>
            </div>
          )}
        </div>

        {/* Sector heatmap */}
        <div>
          <Card padding={false}>
            <CardHeader>{t('sectors')}</CardHeader>
            <div className="p-4">
              {results.length > 0
                ? <SectorHeatmap results={results} mode={mode} />
                : <div className="text-xs text-muted text-center py-4">Uruchom skan</div>
              }
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
