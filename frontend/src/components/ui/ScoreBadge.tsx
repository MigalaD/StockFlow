'use client'

import { clsx } from 'clsx'

type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

interface ScoreBadgeProps {
  score:      number
  size?:      Size
  showLabel?: boolean
  className?: string
}

const SIZE_MAP: Record<Size, { box: string; font: string; ring: number; label: string }> = {
  xs: { box: 'w-8 h-8',   font: 'text-xs',   ring: 2,   label: 'text-[8px]'  },
  sm: { box: 'w-11 h-11', font: 'text-sm',   ring: 2.5, label: 'text-[9px]'  },
  md: { box: 'w-14 h-14', font: 'text-lg',   ring: 3,   label: 'text-[10px]' },
  lg: { box: 'w-20 h-20', font: 'text-2xl',  ring: 3.5, label: 'text-[11px]' },
  xl: { box: 'w-24 h-24', font: 'text-3xl',  ring: 4,   label: 'text-xs'     },
}

export function scoreColor(score: number): string {
  if (score >= 60) return '#22C55E'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

export function scoreLabel(score: number): string {
  if (score >= 60) return 'Pozytywny'
  if (score >= 40) return 'Neutralny'
  return 'Negatywny'
}

/**
 * ScoreBadge — sygnatura produktu.
 * Pierścień postępu (SVG) + liczba w środku. Premium fintech look.
 */
export function ScoreBadge({ score, size = 'md', showLabel, className }: ScoreBadgeProps) {
  const color = scoreColor(score)
  const cfg   = SIZE_MAP[size]
  const pct   = Math.max(0, Math.min(100, score))

  // SVG ring geometry
  const r = 50 - cfg.ring * 2
  const circumference = 2 * Math.PI * r
  const offset = circumference - (pct / 100) * circumference

  return (
    <div className={clsx('inline-flex flex-col items-center gap-1', className)}>
      <div className={clsx('relative', cfg.box)}>
        {/* Progress ring */}
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r={r}
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={cfg.ring} />
          <circle cx="50" cy="50" r={r}
            fill="none" stroke={color} strokeWidth={cfg.ring}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1)' }} />
        </svg>
        {/* Number */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={clsx('font-bold font-mono tabular-nums', cfg.font)} style={{ color }}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      {showLabel && (
        <span className={clsx('uppercase tracking-widest font-semibold', cfg.label)} style={{ color }}>
          {scoreLabel(score)}
        </span>
      )}
    </div>
  )
}

/** Mini pasek — do tabel i list */
export function ScoreBar({ score, width = 'w-16' }: { score: number; width?: string }) {
  const color = scoreColor(score)
  return (
    <div className="flex items-center gap-2">
      <div className={clsx('h-1.5 rounded-full overflow-hidden', width)}
        style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="h-full rounded-full"
          style={{
            width: `${Math.max(0, Math.min(100, score))}%`,
            background: `linear-gradient(90deg, ${color}cc, ${color})`,
            transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)',
          }} />
      </div>
      <span className="text-xs font-bold font-mono tabular-nums w-7 text-right" style={{ color }}>
        {Math.round(score)}
      </span>
    </div>
  )
}
