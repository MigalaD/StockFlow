'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import useSWR from 'swr'
import Link from 'next/link'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { AppShell } from '../../components/layout/AppShell'
import { Card, SectionHeader, Button, Input, EmptyState, Spinner, Tag } from '../../components/ui'
import { scoreColor } from '../../components/ui/ScoreBadge'
import { portfolioApi, type PositionItem } from '../../lib/api'
import { AuthGuard } from '../../components/shared/AuthGuard'

const SECTOR_COLORS = [
  '#22C55E','#14B8A6','#3B82F6','#F59E0B',
  '#8B5CF6','#EC4899','#EF4444','#F97316','#06B6D4',
]

function AddPositionForm({ onAdded }: { onAdded: () => void }) {
  const t = useTranslations('portfolio')
  const [fields, setFields] = useState({ ticker:'', shares:'', price:'', date:'', notes:'' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k: keyof typeof fields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setFields(f => ({ ...f, [k]: k === 'ticker' ? e.target.value.toUpperCase() : e.target.value }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!fields.ticker || !fields.shares || !fields.price) {
      setError('Symbol, liczba akcji i cena są wymagane'); return
    }
    setLoading(true); setError('')
    try {
      await portfolioApi.addPosition({
        ticker:    fields.ticker.trim(),
        shares:    parseFloat(fields.shares),
        buy_price: parseFloat(fields.price),
        buy_date:  fields.date || undefined,
        notes:     fields.notes || undefined,
      })
      setFields({ ticker:'', shares:'', price:'', date:'', notes:'' })
      onAdded()
    } catch (err: any) { setError(err.detail ?? 'Błąd')
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-surface border border-border rounded-xl2 p-4">
      <div className="font-semibold text-sm text-white mb-4">➕ {t('addPosition')}</div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <Input label={t('ticker')}   value={fields.ticker} onChange={set('ticker')} placeholder="AAPL" hint="GPW: .WA" />
          <Input label={t('shares')}   value={fields.shares} onChange={set('shares')} type="number" placeholder="10" min="0.001" step="any" />
          <Input label={t('buyPrice')} value={fields.price}  onChange={set('price')}  type="number" placeholder="185.50" min="0.001" step="any" />
          <Input label={t('buyDate')}  value={fields.date}   onChange={set('date')}   type="date" />
        </div>
        <div className="mb-3">
          <Input label={t('notes')} value={fields.notes} onChange={set('notes')} placeholder="Opcjonalna notatka..." />
        </div>
        {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-3">{error}</div>}
        <Button type="submit" loading={loading} size="sm">{t('addPosition')}</Button>
      </form>
    </div>
  )
}

function PositionCard({ pos, onRemove }: { pos: PositionItem; onRemove: () => void }) {
  const pnlPos  = pos.pnl >= 0
  const pnlColor = pnlPos ? '#22C55E' : '#EF4444'
  return (
    <div className="bg-surface border border-border rounded-xl2 p-4" style={{ borderLeft: `3px solid ${pnlColor}` }}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-white">{pos.ticker}</span>
            {pos.sector && <Tag className="text-muted text-[10px]">{pos.sector}</Tag>}
          </div>
          <div className="text-xs text-muted mt-0.5 truncate max-w-[200px]">{pos.name}</div>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold tabular-nums" style={{ color: pnlColor }}>
            {pnlPos ? '+' : ''}{pos.pnl.toFixed(2)} {pos.currency}
          </div>
          <div className="text-sm font-semibold" style={{ color: pnlColor }}>
            {pnlPos ? '+' : ''}{pos.pnl_pct.toFixed(2)}%
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center mb-3">
        {[
          { label:'Zakup',   value:`${pos.buy_price.toFixed(2)}`,    sub:`${pos.shares}×`  },
          { label:'Teraz',   value:`${pos.current_price.toFixed(2)}`, sub:pos.currency     },
          { label:'Wartość', value:`${pos.current_value.toFixed(2)}`, sub:pos.currency     },
        ].map(m => (
          <div key={m.label} className="bg-surface-hi rounded-lg p-2">
            <div className="text-[10px] text-muted uppercase tracking-wider">{m.label}</div>
            <div className="font-bold tabular-nums text-sm text-white mt-0.5">{m.value}</div>
            <div className="text-[10px] text-muted">{m.sub}</div>
          </div>
        ))}
      </div>
      {(pos.buy_date || pos.notes) && (
        <div className="text-xs text-muted flex gap-3 mb-2.5">
          {pos.buy_date && <span>📅 {pos.buy_date}</span>}
          {pos.notes    && <span>📝 {pos.notes}</span>}
        </div>
      )}
      <div className="flex items-center justify-between">
        <Link href={`/analysis?ticker=${pos.ticker}`}>
          <Button variant="ghost" size="sm">Analizuj →</Button>
        </Link>
        <button onClick={onRemove} className="text-xs text-muted hover:text-red-400 transition-colors">
          Usuń
        </button>
      </div>
    </div>
  )
}

function AllocationChart({ allocation }: { allocation: Record<string, number> }) {
  const data = Object.entries(allocation)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value], i) => ({ name, value: Math.round(value * 10) / 10, color: SECTOR_COLORS[i % SECTOR_COLORS.length] }))

  if (!data.length) return null
  return (
    <div className="bg-surface border border-border rounded-xl2 p-4">
      <SectionHeader title="Alokacja sektorowa" icon="🥧" />
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={2} dataKey="value">
            {data.map((e, i) => <Cell key={i} fill={e.color} />)}
          </Pie>
          <Tooltip
            formatter={(v: number) => [`${v}%`, 'Udział']}
            contentStyle={{ background:'#111827', border:'1px solid rgba(255,255,255,0.07)', borderRadius:8 }}
            labelStyle={{ color:'#F8FAFC' }}
          />
          <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ color:'#94A3B8', fontSize:11 }}>{v}</span>} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

function PortfolioContent() {
  const t = useTranslations('portfolio')
  const { data: portfolio, isLoading, mutate } = useSWR('portfolio', portfolioApi.get)

  const totalPnlPos = (portfolio?.total_pnl ?? 0) >= 0

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold">{t('title')}</h1>
        {portfolio && portfolio.positions.length > 0 && (
          <div className="flex gap-6">
            {[
              { label:'Łączna wartość', value:`${portfolio.total_value.toFixed(2)}`, color:'#F8FAFC' },
              { label:t('totalPnl'),
                value:`${totalPnlPos?'+':''}${portfolio.total_pnl.toFixed(2)} (${totalPnlPos?'+':''}${portfolio.total_pnl_pct.toFixed(2)}%)`,
                color: totalPnlPos ? '#22C55E' : '#EF4444' },
            ].map(s => (
              <div key={s.label} className="text-right">
                <div className="text-[10px] text-muted uppercase tracking-wider">{s.label}</div>
                <div className="text-lg font-bold tabular-nums" style={{ color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {portfolio?.warnings.map((w, i) => (
        <div key={i} className="mb-3 rounded-lg px-4 py-2.5 text-sm"
          style={{ background:'rgba(245,158,11,0.1)', color:'#F59E0B', border:'1px solid rgba(245,158,11,0.2)' }}>
          ⚠ {w}
        </div>
      ))}

      <div className="grid grid-cols-[1fr_260px] gap-5">
        <div className="space-y-4">
          <AddPositionForm onAdded={() => mutate()} />
          {isLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : !portfolio || portfolio.positions.length === 0 ? (
            <EmptyState icon="💼" title={t('empty')} desc={t('emptyHint')} />
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              {portfolio.positions.map(pos => (
                <PositionCard key={pos.id} pos={pos} onRemove={async () => { await portfolioApi.removePosition(pos.id); mutate() }} />
              ))}
            </div>
          )}
        </div>
        <div>
          {portfolio && <AllocationChart allocation={portfolio.allocation_by_sector} />}
        </div>
      </div>
    </AppShell>
  )
}

export default function PortfolioPage() {
  return <AuthGuard><PortfolioContent /></AuthGuard>
}
