'use client'
import { AlertTriangle, BarChart3, Briefcase, CalendarDays, ClipboardList, Download, PieChart, Plus, StickyNote } from 'lucide-react'

import { useState } from 'react'
import useSWR from 'swr'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { SectionHeader, Button, Input, EmptyState, Spinner, Tag } from '../../components/ui'
import { scoreColor } from '../../components/ui/ScoreBadge'
import { portfolioApi, type PositionItem } from '../../lib/api'

const SECTOR_COLORS = [
  '#22C55E','#14B8A6','#3B82F6','#F59E0B',
  '#8B5CF6','#EC4899','#EF4444','#F97316','#06B6D4',
]

// ── Add position form ─────────────────────────────────────────────────

function AddPositionForm({ onAdded, onToggleImport }: { onAdded: () => void; onToggleImport: () => void }) {
  const [open, setOpen] = useState(false)
  const [fields, setFields] = useState({ ticker:'', shares:'', price:'', date:'', notes:'' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k: keyof typeof fields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setFields(f => ({ ...f, [k]: k === 'ticker' ? e.target.value.toUpperCase() : e.target.value }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!fields.ticker || !fields.shares || !fields.price) {
      setError('Symbol, liczba i cena są wymagane'); return
    }
    setLoading(true); setError('')
    try {
      await portfolioApi.addPosition({
        ticker: fields.ticker.trim(), shares: parseFloat(fields.shares),
        buy_price: parseFloat(fields.price), buy_date: fields.date || undefined,
        notes: fields.notes || undefined,
      })
      setFields({ ticker:'', shares:'', price:'', date:'', notes:'' })
      setOpen(false)
      onAdded()
    } catch (err: any) { setError(err.detail ?? 'Błąd')
    } finally { setLoading(false) }
  }

  if (!open) return (
    <div className="flex gap-2 mb-4">
      <Button onClick={() => setOpen(true)} size="sm">
        Dodaj pozycję
      </Button>
      <Button onClick={onToggleImport} size="sm" variant="secondary">
        Import z XTB
      </Button>
    </div>
  )

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold text-sm text-white flex items-center gap-2"><Plus className="w-4 h-4 text-brand-green" /> Nowa pozycja</div>
        <button onClick={() => setOpen(false)} className="text-muted hover:text-white text-sm">✕</button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <Input label={t('symbol')}     value={fields.ticker} onChange={set('ticker')} placeholder="AAPL" hint="GPW: .WA" />
          <Input label={t('shares')} type="number" value={fields.shares} onChange={set('shares')} placeholder="10" min="0.001" step="any" />
          <Input label={t('buyPrice')} type="number" value={fields.price}  onChange={set('price')}  placeholder="185.50" min="0.001" step="any" />
          <Input label={t('buyDate')} type="date"   value={fields.date}   onChange={set('date')} />
        </div>
        <div className="mb-3">
          <Input label={t('noteOptional')} value={fields.notes} onChange={set('notes')} placeholder={t('reasonPlaceholder')} />
        </div>
        {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-3">{error}</div>}
        <div className="flex gap-2">
          <Button type="submit" loading={loading} size="sm">Dodaj</Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>{t('cancel')}</Button>
        </div>
      </form>
    </div>
  )
}

// ── Position card ─────────────────────────────────────────────────────

function PositionCard({ pos, onRemove }: { pos: PositionItem; onRemove: () => void }) {
  const [confirm, setConfirm] = useState(false)
  const pnlPos  = pos.pnl >= 0
  const pnlColor = pnlPos ? '#22C55E' : '#EF4444'
  const pct     = ((pos.current_price - pos.buy_price) / pos.buy_price * 100)

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4"
      style={{ borderLeft: `3px solid ${pnlColor}` }}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <Link href={`/analysis?ticker=${pos.ticker}`}>
              <span className="font-bold text-white hover:text-brand-green transition-colors">
                {pos.ticker}
              </span>
            </Link>
            {pos.sector && <Tag className="text-[10px]">{pos.sector}</Tag>}
            {pos.score != null && (
              <span className="text-xs font-bold tabular-nums"
                style={{ color: scoreColor(pos.score) }}>{Math.round(pos.score)}</span>
            )}
          </div>
          <div className="text-xs text-muted mt-0.5 truncate max-w-[200px]">{pos.name}</div>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold tabular-nums" style={{ color: pnlColor }}>
            {pnlPos ? '+' : ''}{pos.pnl.toFixed(2)} {pos.currency}
          </div>
          <div className="text-sm font-semibold" style={{ color: pnlColor }}>
            {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 text-center mb-3">
        {[
          { label:'Zakup',    value:`${pos.buy_price.toFixed(2)}`,    sub:`${pos.shares}×` },
          { label:'Teraz',    value:`${pos.current_price.toFixed(2)}`, sub:pos.currency     },
          { label:'Wartość',  value:`${pos.current_value.toFixed(0)}`, sub:pos.currency     },
          { label:'Udział',   value:'—',                               sub:'w portfolio'    },
        ].map(m => (
          <div key={m.label} className="bg-surface-2 rounded-lg p-2">
            <div className="text-[10px] text-muted uppercase tracking-wider">{m.label}</div>
            <div className="font-bold tabular-nums text-sm text-white mt-0.5">{m.value}</div>
            <div className="text-[10px] text-muted">{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Progress bar: cena zakupu → cena bieżąca */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] text-muted mb-1">
          <span>Zakup: {pos.buy_price.toFixed(2)}</span>
          <span>Teraz: {pos.current_price.toFixed(2)}</span>
        </div>
        <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
          <div className="h-full rounded-full" style={{
            width: `${Math.min(Math.max((pos.current_price / pos.buy_price) * 50, 0), 100)}%`,
            background: pnlColor,
          }} />
        </div>
      </div>

      {(pos.buy_date || pos.notes) && (
        <div className="text-xs text-muted flex gap-3 mb-2">
          {pos.buy_date && <span className="flex items-center gap-1"><CalendarDays className="w-3 h-3" />{pos.buy_date}</span>}
          {pos.notes    && <span className="truncate flex items-center gap-1"><StickyNote className="w-3 h-3 shrink-0" />{pos.notes}</span>}
        </div>
      )}

      <div className="flex items-center justify-between">
        <Link href={`/analysis?ticker=${pos.ticker}`}>
          <Button variant="ghost" size="sm">{t('analyze')}</Button>
        </Link>
        {confirm ? (
          <div className="flex gap-2">
            <button onClick={onRemove} className="text-xs text-red-400 hover:text-red-300">{t('confirm')}</button>
            <button onClick={() => setConfirm(false)} className="text-xs text-muted hover:text-white">{t('cancel')}</button>
          </div>
        ) : (
          <button onClick={() => setConfirm(true)} className="text-xs text-muted hover:text-red-400 transition-colors">
            Usuń
          </button>
        )}
      </div>
    </div>
  )
}

// ── Portfolio page ────────────────────────────────────────────────────

// ── Import z XTB (CSV z xStation) ─────────────────────────────────────

type ParsedPos = { ticker: string; shares: number; buy_price: number; buy_date?: string }

/**
 * Normalizuje symbol XTB do formatu yfinance.
 * Zweryfikowane na realnym eksporcie: .PL→.WA, .US→(brak), .UK→.L (Londyn),
 * .NO→.OL (Oslo), .DE zostaje bez zmian (Xetra — te same tickery co Yahoo).
 * Nieznany sufiks zostaje bez zmian — widoczny w podglądzie do ręcznej korekty.
 */
function normalizeXtbSymbol(sym: string): string {
  const s = sym.trim().toUpperCase()
  if (s.endsWith('.PL')) return s.replace(/\.PL$/, '.WA')
  if (s.endsWith('.US')) return s.replace(/\.US$/, '')
  if (s.endsWith('.UK')) return s.replace(/\.UK$/, '.L')
  if (s.endsWith('.NO')) return s.replace(/\.NO$/, '.OL')
  return s
}

/**
 * Parsuje CSV z XTB — eksport "Open positions" (otwarte pozycje).
 *
 * Realny plik XTB (zweryfikowany na przykładowym eksporcie) ma ok. 10-13
 * linii "śmieci" przed właściwym nagłówkiem: puste wiersze, dane konta,
 * blok Balance/Equity/Margin, tytuł sekcji, zakres dat. Separator to
 * średnik, liczby z przecinkiem dziesiętnym, plik z BOM UTF-8.
 *
 * Nagłówek szukany DYNAMICZNIE (nie zakładamy stałej liczby wierszy
 * śmieci) — skanujemy linie aż znajdziemy taką, która zawiera zarówno
 * "symbol" jak i "volume". To też odróżnia format otwartych pozycji
 * (Open time/Open price/Market price) od historii zamkniętych transakcji
 * (Open time+Close time+Close price) — jeśli w nagłówku jest "close
 * price"/"close time", zwracamy ostrzeżenie zamiast cichego zaimportowania
 * dawno zamkniętych transakcji jako aktywnych pozycji.
 */
function parseXtbCsv(text: string): { positions: ParsedPos[]; skipped: string[]; warning?: string } {
  // Usuń BOM, jeśli obecny
  const clean = text.replace(/^\uFEFF/, '')
  const rawLines = clean.split(/\r?\n/)

  const splitLine = (line: string, sep: string) =>
    line.split(sep).map(c => c.trim().replace(/"/g, ''))

  // Znajdź linię nagłówka — pierwszą zawierającą "symbol" ORAZ "volume"
  // (niezależnie od separatora — sprawdzamy każdy kandydat na tej linii)
  let headerIdx = -1
  let sep = ';'
  let headers: string[] = []

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i]
    if (!line.trim()) continue
    for (const candidateSep of [';', '\t', ',']) {
      const cols = splitLine(line, candidateSep).map(c => c.toLowerCase())
      if (cols.some(c => c.includes('symbol')) && cols.some(c => c.includes('volume') || c.includes('wolumen'))) {
        headerIdx = i
        sep = candidateSep
        headers = cols
        break
      }
    }
    if (headerIdx >= 0) break
  }

  if (headerIdx < 0) {
    return { positions: [], skipped: [], warning: 'Nie znaleziono nagłówka z kolumnami Symbol/Volume w pliku. Upewnij się, że to eksport CSV z XTB (raport "Open positions").' }
  }

  const findCol = (...names: string[]) =>
    headers.findIndex(h => names.some(n => h.includes(n)))

  const iSym   = findCol('symbol', 'instrument')
  const iVol   = findCol('volume', 'wolumen', 'ilość', 'ilosc')
  const iPrice = findCol('open price', 'cena otwarcia')
  const iDate  = findCol('open time', 'czas otwarcia')
  const hasClose = headers.some(h => h.includes('close price') || h.includes('close time'))

  if (iSym < 0 || iVol < 0 || iPrice < 0) {
    return { positions: [], skipped: [], warning: 'Rozpoznano nagłówek, ale brakuje kolumn Symbol/Volume/Open price.' }
  }

  const warning = hasClose
    ? 'Ten plik wygląda na historię ZAMKNIĘTYCH pozycji (ma kolumny Close price/Close time), nie aktualny portfel. ' +
      'W xStation wybierz raport "Open positions" (otwarte pozycje), żeby zaimportować to, co faktycznie posiadasz.'
    : undefined

  const positions: ParsedPos[] = []
  const skipped: string[] = []
  const num = (v?: string) => v ? parseFloat(v.replace(/\s/g, '').replace(',', '.')) : NaN

  for (const line of rawLines.slice(headerIdx + 1)) {
    if (!line.trim()) continue
    const cols = splitLine(line, sep)
    const rawSym = cols[iSym]
    // Wiersz podsumowania ("Total") albo pusty symbol — koniec danych
    if (!rawSym || /^total$/i.test(rawSym)) continue

    const shares = num(cols[iVol])
    const price  = num(cols[iPrice])
    if (!shares || !price || shares <= 0 || price <= 0) {
      skipped.push(rawSym)
      continue
    }
    // Format XTB: "30.04.2026 10:03:04" (DD.MM.RRRR GG:MM:SS) -> ISO RRRR-MM-DD
    const dateRaw = iDate >= 0 ? cols[iDate] : undefined
    let buy_date: string | undefined
    if (dateRaw) {
      const datePart = dateRaw.split(' ')[0]
      const m = datePart.match(/^(\d{2})\.(\d{2})\.(\d{4})$/)
      buy_date = m ? `${m[3]}-${m[2]}-${m[1]}` : undefined
    }
    positions.push({ ticker: normalizeXtbSymbol(rawSym), shares, buy_price: price, buy_date })
  }
  return { positions, skipped, warning }
}

function XtbImport({ onDone }: { onDone: () => void }) {
  const [parsed, setParsed]   = useState<{ positions: ParsedPos[]; skipped: string[]; warning?: string } | null>(null)
  const [busy, setBusy]       = useState(false)
  const [result, setResult]   = useState('')

  async function handleFile(f: File) {
    const text = await f.text()
    setParsed(parseXtbCsv(text))
    setResult('')
  }

  async function doImport() {
    if (!parsed?.positions.length) return
    setBusy(true)
    try {
      const res = await portfolioApi.importPositions(parsed.positions)
      setResult(`Zaimportowano ${res.added} pozycji${res.errors.length ? `, błędy: ${res.errors.length}` : ''}.`)
      setParsed(null)
      onDone()
    } catch (err: any) {
      setResult(err?.detail ?? 'Import nie powiódł się.')
    } finally { setBusy(false) }
  }

  return (
    <div className="bg-surface-1 border border-border rounded-xl2 p-4 mb-4 animate-fade-in">
      <div className="font-semibold text-sm text-text-hi mb-1 flex items-center gap-2"><Download className="w-4 h-4 text-brand-green" /> Import z XTB</div>
      <p className="text-xs text-text-lo mb-3 leading-relaxed">
        W xStation: Historia → Sprawozdania → wybierz raport <strong className="text-text-mid">„Open positions"</strong> (otwarte pozycje) →
        eksport do CSV, a plik wgraj tutaj. Nie „Closed position history" — to zamknięte, już nieaktualne transakcje.
        Symbole dopasujemy automatycznie (PKN.PL→PKN.WA, IGLN.UK→IGLN.L, KMAR.NO→KMAR.OL).
      </p>
      <input type="file" accept=".csv,.txt" className="text-xs text-text-lo mb-3 block"
        onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />

      {parsed && (
        <div className="space-y-2">
          {parsed.warning && (
            <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 leading-relaxed">
              <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />{parsed.warning}
            </div>
          )}
          {parsed.positions.length > 0 ? (
            <>
              <div className="text-xs text-text-lo">
                Rozpoznano <strong className="text-text-hi">{parsed.positions.length}</strong> pozycji:
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
                {parsed.positions.map((p, i) => (
                  <div key={i} className="flex gap-3 text-xs font-mono bg-surface-2 rounded-md px-2.5 py-1.5">
                    <span className="font-bold text-text-hi w-20">{p.ticker}</span>
                    <span className="text-muted">{p.shares} szt.</span>
                    <span className="text-muted">@ {p.buy_price}</span>
                    {p.buy_date && <span className="text-muted ml-auto">{p.buy_date}</span>}
                  </div>
                ))}
              </div>
              <Button onClick={doImport} loading={busy} size="sm">
                Importuj {parsed.positions.length} pozycji
              </Button>
            </>
          ) : (
            <div className="text-xs text-red-400">{t('importNoPositions')}</div>
          )}
          {parsed.skipped.length > 0 && (
            <div className="text-2xs text-muted">Pominięte wiersze: {parsed.skipped.join(', ')}</div>
          )}
        </div>
      )}
      {result && <div className="text-xs text-brand-green mt-2">{result}</div>}
    </div>
  )
}

function PortfolioContent() {
  const t = useTranslations('portfolio')
  const { data: portfolio, isLoading, mutate } = useSWR('portfolio', portfolioApi.get)
  const [showImport, setShowImport] = useState(false)

  const totalPnlPos = (portfolio?.total_pnl ?? 0) >= 0
  const positions   = portfolio?.positions ?? []

  // Dane do wykresu słupkowego P&L
  const pnlChartData = positions
    .map(p => ({ ticker: p.ticker, pnl: Math.round(p.pnl * 100) / 100, pct: Math.round(p.pnl_pct * 100) / 100 }))
    .sort((a, b) => b.pnl - a.pnl)

  // Alokacja sektorowa
  const allocationData = Object.entries(portfolio?.allocation_by_sector ?? {})
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value], i) => ({
      name, value: Math.round(value * 10) / 10,
      color: SECTOR_COLORS[i % SECTOR_COLORS.length],
    }))

  return (
    <AppShell>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold flex items-center gap-2"><Briefcase className="w-5 h-5 text-brand-green" /> Portfolio</h1>
        {portfolio && positions.length > 0 && (
          <div className="flex gap-5">
            <div className="text-right">
              <div className="text-[10px] text-muted uppercase tracking-wider">{t('totalValue')}</div>
              <div className="text-lg font-bold tabular-nums font-mono text-text-hi">
                {portfolio.total_value.toFixed(2)}
                <span className="text-sm text-muted ml-1">{portfolio.base_currency}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-muted uppercase tracking-wider">P&L łącznie</div>
              <div className="text-lg font-bold tabular-nums font-mono" style={{ color: totalPnlPos ? '#22C55E' : '#EF4444' }}>
                {totalPnlPos ? '+' : ''}{portfolio.total_pnl.toFixed(2)}
                <span className="text-sm text-muted ml-1">{portfolio.base_currency}</span>
                <span className="text-sm ml-1">({totalPnlPos ? '+' : ''}{portfolio.total_pnl_pct.toFixed(2)}%)</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Warnings */}
      {portfolio?.warnings.map((w, i) => (
        <div key={i} className="mb-3 rounded-lg px-4 py-2.5 text-sm"
          style={{ background:'rgba(245,158,11,0.1)', color:'#F59E0B', border:'1px solid rgba(245,158,11,0.2)' }}>
          <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />{w}
        </div>
      ))}


      {/* Portfel vs S&P 500 */}
      {portfolio?.benchmark && (
        <div className="bg-surface-1 border border-border rounded-xl2 p-4 mb-4 animate-fade-in">
          <div className="text-2xs text-muted uppercase tracking-widest mb-2">{t('benchmarkTitle')} {portfolio.benchmark.symbol}</div>
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <div><span className="text-2xs text-muted mr-1.5">{t('yourPortfolio')}</span>
              <span className="font-mono font-bold text-sm" style={{ color: portfolio.benchmark.portfolio_pnl_pct >= 0 ? '#22C55E' : '#EF4444' }}>
                {portfolio.benchmark.portfolio_pnl_pct >= 0 ? '+' : ''}{portfolio.benchmark.portfolio_pnl_pct}%</span></div>
            <div><span className="text-2xs text-muted mr-1.5">{portfolio.benchmark.symbol} {t('inSamePeriod')}</span>
              <span className="font-mono font-bold text-sm text-text-lo">
                {portfolio.benchmark.benchmark_pnl_pct >= 0 ? '+' : ''}{portfolio.benchmark.benchmark_pnl_pct}%</span></div>
            <div><span className="text-2xs text-muted mr-1.5">{t('difference')}</span>
              <span className="font-mono font-bold text-sm" style={{ color: portfolio.benchmark.alpha >= 0 ? '#22C55E' : '#EF4444' }}>
                {portfolio.benchmark.alpha >= 0 ? '+' : ''}{portfolio.benchmark.alpha} p.p.</span></div>
          </div>
          <p className="text-2xs text-muted mt-1.5">{t('benchmarkNote')}</p>
        </div>
      )}

      <AddPositionForm onAdded={() => mutate()} onToggleImport={() => setShowImport(v => !v)} />
      {showImport && <XtbImport onDone={() => mutate()} />}

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : !portfolio || positions.length === 0 ? (
        <EmptyState icon={Briefcase} title={t('empty')}
          desc={t('emptyHint')} />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5">
          {/* Positions */}
          <div>
            <SectionHeader title={t('positions')} icon={ClipboardList} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {positions.map(pos => (
                <PositionCard key={pos.id} pos={pos}
                  onRemove={async () => { await portfolioApi.removePosition(pos.id); mutate() }} />
              ))}
            </div>
          </div>

          {/* Charts */}
          <div className="space-y-4">
            {/* Alokacja pie */}
            {allocationData.length > 0 && (
              <div className="bg-surface-1 border border-border rounded-xl2 p-4">
                <SectionHeader title={t('sectorAllocation')} icon={PieChart} />
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={allocationData} cx="50%" cy="50%"
                      innerRadius={50} outerRadius={80} paddingAngle={2} dataKey="value">
                      {allocationData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Pie>
                    <Tooltip
                      formatter={(v: number) => [`${v}%`, 'Udział']}
                      contentStyle={{ background:'#111827', border:'1px solid rgba(255,255,255,0.07)', borderRadius:8 }}
                      labelStyle={{ color:'#F8FAFC' }}
                    />
                    <Legend iconType="circle" iconSize={8}
                      formatter={(v) => <span style={{ color:'#94A3B8', fontSize:11 }}>{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* P&L bar chart */}
            {pnlChartData.length > 0 && (
              <div className="bg-surface-1 border border-border rounded-xl2 p-4">
                <SectionHeader title="P&L per pozycja" icon={BarChart3} />
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={pnlChartData} margin={{ top:4, right:4, bottom:4, left:4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="ticker" tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} />
                    <YAxis tick={{ fill:'#64748B', fontSize:10 }} tickLine={false} width={40} />
                    <Tooltip
                      formatter={(v: number) => [`${v > 0 ? '+' : ''}${v.toFixed(2)}`, 'P&L']}
                      contentStyle={{ background:'#111827', border:'1px solid rgba(255,255,255,0.07)', borderRadius:8 }}
                      labelStyle={{ color:'#F8FAFC' }}
                    />
                    <Bar dataKey="pnl" radius={[3,3,0,0]}>
                      {pnlChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.pnl >= 0 ? '#22C55E' : '#EF4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default function PortfolioPage() {
  return <PortfolioContent />
}
