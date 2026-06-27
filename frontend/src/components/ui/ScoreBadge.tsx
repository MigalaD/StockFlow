'use client'

import { clsx } from 'clsx'

type Size = 'sm' | 'md' | 'lg' | 'xl'

interface ScoreBadgeProps {
  score:     number
  size?:     Size
  showLabel?: boolean
  className?: string
}

const SIZE_MAP: Record<Size, {
  outer: string
  font:  string
  border: string
}> = {
  sm: { outer: 'w-10 h-10',   font: 'text-sm',    border: 'border-[1.5px]' },
  md: { outer: 'w-14 h-14',   font: 'text-lg',    border: 'border-2'       },
  lg: { outer: 'w-20 h-20',   font: 'text-2xl',   border: 'border-2'       },
  xl: { outer: 'w-24 h-24',   font: 'text-3xl',   border: 'border-[3px]'   },
}

export function scoreColor(score: number): string {
  if (score >= 60) return '#22C55E'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

export function scoreLabel(score: number): string {
  if (score >= 60) return 'Positive'
  if (score >= 40) return 'Neutral'
  return 'Negative'
}

export function ScoreBadge({ score, size = 'md', showLabel, className }: ScoreBadgeProps) {
  const color  = scoreColor(score)
  const config = SIZE_MAP[size]

  return (
    <div className={clsx('flex flex-col items-center gap-1', className)}>
      <div
        className={clsx(
          'rounded-full flex items-center justify-center',
          'font-bold tabular-nums shrink-0',
          config.outer,
          config.font,
          config.border,
        )}
        style={{
          color,
          borderColor:     color,
          backgroundColor: color + '18',
        }}
      >
        {Math.round(score)}
      </div>
      {showLabel && (
        <span
          className="text-2xs uppercase tracking-widest font-semibold"
          style={{ color }}
        >
          {scoreLabel(score)}
        </span>
      )}
    </div>
  )
}

/** Mini progress bar — używana w tabelach skanera */
export function ScoreBar({ score, width = 'w-16' }: { score: number; width?: string }) {
  const color = scoreColor(score)
  return (
    <div className="flex items-center gap-2">
      <div className={clsx('h-1 rounded-full bg-surface-hi overflow-hidden', width)}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span
        className="text-xs font-bold tabular-nums w-6 text-right"
        style={{ color }}
      >
        {Math.round(score)}
      </span>
    </div>
  )
}
