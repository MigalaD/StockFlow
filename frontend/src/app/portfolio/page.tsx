'use client'

import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { SectionHeader, Button, Input, EmptyState, Spinner, Tag } from '../../components/ui'
import { scoreColor } from '../../components/ui/ScoreBadge'
import { portfolioApi, type PositionItem } from '../../lib/api'
import { AuthGuard } from '../../components/shared/AuthGuard'

const SECTOR_COLORS = [
  '#22C55E','#14B8A6','#3B82F6','#F59E0B',
  '#8B5CF6','#EC4899','#EF4444','#F97316','#06B6D4',
]

// ── Add position form ─────────────────────────────────────────────────

function AddPositionForm({ onAdded }: { onAdded: () => void }) {
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
    <Button onClick={() => setOpen(true)} size="sm" className="mb-4">
      ➕ Dodaj pozycję
    </Button>
  )

  return (
    <div className="bg-surface border border-border rounded-xl2 p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold text-sm text-white">➕ Nowa pozycja</div>
        <button onClick={() => setOpen(false)} className="text-muted hover:text-white text-sm">✕</button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <Input label="Symbol"     value={fields.ticker} onChange={set('ticker')} placeholder="AAPL" hint="GPW: .WA" />
          <Input label="Liczba szt." type="number" value={fields.shares} onChange={set('shares')} placeholder="10" min="0.001" step="any" />
          <Input label="Cena zakupu" type="number" value={fields.price}  onChange={set('price')}  placeholder="185.50" min="0.001" step="any" />
          <Input label="Data zakupu" type="date"   value={fields.date}   onChange={set('date')} />
        </div>
        <div className="mb-3">
          <Input label="Notatka (opcjonalna)" value={fields.notes} onChange={set('notes')} placeholder="Powód zakupu..." />
        </div>
        {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-3">{error}</div>}
        <div className="flex gap-2">
          <Button type="submit" loading={loading} size="sm">Dodaj</Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Anuluj</Button>
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
    <div className="bg-surface border border-border rounded-xl2 p-4"
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
          <div key={m.label} className="bg-surface-hi rounded-lg p-2">
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
        <div className="h-1.5 rounded-full bg-surface-hi overflow-hidden">
          <div className="h-full rounded-full" style={{
            width: `${Math.min(Math.max((pos.current_price / pos.buy_price) * 50, 0), 100)}%`,
            background: pnlColor,
          }} />
        </div>
      </div>

      {(pos.buy_date || pos.notes) && (
        <div className="text-xs text-muted flex gap-3 mb-2">
          {pos.buy_date && <span>📅 {pos.buy_date}</span>}
          {pos.notes    && <span className="truncate">📝 {pos.notes}</span>}
        </div>
      )}

      <div className="flex items-center justify-between">
        <Link href={`/analysis?ticker=${pos.ticker}`}>
          <Button variant="ghost" size="sm">Analizuj →</Button>
        </Link>
        {confirm ? (
          <div className="flex gap-2">
            <button onClick={onRemove} className="text-xs text-red-400 hover:text-red-300">Potwierdź</button>
            <button onClick={() => setConfirm(false)} className="text-xs text-muted hover:text-white">Anuluj</button>
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

function PortfolioContent() {
  const { data: portfolio, isLoading, mutate } = useSWR('portfolio', portfolioApi.get)

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
        <h1 className="text-xl font-bold">💼 Portfolio</h1>
        {portfolio && positions.length > 0 && (
          <div className="flex gap-5">
            <div className="text-right">
              <div className="text-[10px] text-muted uppercase tracking-wider">Łączna wartość</div>
              <div className="text-lg font-bold tabular-nums text-white">
                {portfolio.total_value.toFixed(2)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-muted uppercase tracking-wider">P&L łącznie</div>
              <div className="text-lg font-bold tabular-nums" style={{ color: totalPnlPos ? '#22C55E' : '#EF4444' }}>
                {totalPnlPos ? '+' : ''}{portfolio.total_pnl.toFixed(2)}
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
          ⚠ {w}
        </div>
      ))}

      <AddPositionForm onAdded={() => mutate()} />

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : !portfolio || positions.length === 0 ? (
        <EmptyState icon="💼" title="Portfolio jest puste"
          desc="Dodaj pierwszą pozycję aby śledzić swoje wyniki" />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5">
          {/* Positions */}
          <div>
            <SectionHeader title="Pozycje" icon="📋" />
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
              <div className="bg-surface border border-border rounded-xl2 p-4">
                <SectionHeader title="Alokacja sektorowa" icon="🥧" />
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
              <div className="bg-surface border border-border rounded-xl2 p-4">
                <SectionHeader title="P&L per pozycja" icon="📊" />
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
  return <AuthGuard><PortfolioContent /></AuthGuard>
}
