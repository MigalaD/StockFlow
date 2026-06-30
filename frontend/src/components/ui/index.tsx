'use client'

import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'
import type { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from 'react'

// ═══════════════════════════════════════════════════════════════════════
// Card
// ═══════════════════════════════════════════════════════════════════════

interface CardProps {
  children:     ReactNode
  className?:   string
  accent?:      string    // border-left color hex
  padding?:     boolean
  interactive?: boolean
}

export function Card({ children, className, accent, padding = true, interactive }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-xl2 border border-border bg-surface-1 transition-colors',
        padding && 'p-5',
        interactive && 'cursor-pointer hover:bg-surface-2 hover:border-border-hi',
        className,
      )}
      style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  children,
  className,
  action,
}: {
  children:   ReactNode
  className?: string
  action?:    ReactNode
}) {
  return (
    <div className={clsx(
      'flex items-center justify-between px-5 py-3.5 border-b border-border',
      className,
    )}>
      <div className="font-semibold text-sm text-text-hi">{children}</div>
      {action && <div>{action}</div>}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Button
// ═══════════════════════════════════════════════════════════════════════

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant
  size?:     'sm' | 'md' | 'lg'
  loading?:  boolean
  icon?:     ReactNode
  children?: ReactNode
}

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
}

export function Button({
  variant = 'primary',
  size    = 'md',
  loading,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  // Use the design-system classes for primary/secondary/ghost (defined in globals.css)
  const variantClass =
    variant === 'primary'   ? 'btn-primary'
  : variant === 'secondary' ? 'btn-secondary'
  : variant === 'ghost'     ? 'btn-ghost'
  : ''  // danger handled inline below

  return (
    <button
      className={clsx(
        variantClass,
        variant === 'danger' && clsx(
          'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all',
          'border border-red-500/60 text-red-400 hover:bg-red-500/10 hover:border-red-500',
          'disabled:opacity-45 disabled:cursor-not-allowed',
        ),
        SIZE_CLASSES[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Input
// ═══════════════════════════════════════════════════════════════════════

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?:    string
  error?:    string
  hint?:     string
  prefixEl?: ReactNode
}

export function Input({ label, error, hint, prefixEl, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-2xs font-semibold text-muted uppercase tracking-wider">
          {label}
        </label>
      )}
      <div className="relative">
        {prefixEl && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm pointer-events-none">
            {prefixEl}
          </span>
        )}
        <input
          className={clsx(
            'input',
            prefixEl && 'pl-9',
            error && '!border-red-500',
            className,
          )}
          {...props}
        />
      </div>
      {error && <span className="text-xs text-red-400">{error}</span>}
      {hint && !error && <span className="text-2xs text-muted">{hint}</span>}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Tag
// ═══════════════════════════════════════════════════════════════════════

interface TagProps {
  children:   ReactNode
  color?:     string
  className?: string
}

export function Tag({ children, color, className }: TagProps) {
  return (
    <span
      className={clsx('tag', className)}
      style={color ? {
        color,
        borderColor:     color + '40',
        backgroundColor: color + '14',
      } : undefined}
    >
      {children}
    </span>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Spinner
// ═══════════════════════════════════════════════════════════════════════

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }[size]
  return <Loader2 className={clsx('animate-spin text-brand-green', sizeClass)} />
}


// ═══════════════════════════════════════════════════════════════════════
// Skeleton — loading placeholder
// ═══════════════════════════════════════════════════════════════════════

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton rounded-md', className)} />
}


// ═══════════════════════════════════════════════════════════════════════
// EmptyState
// ═══════════════════════════════════════════════════════════════════════

interface EmptyStateProps {
  icon:    string
  title:   string
  desc:    string
  action?: ReactNode
}

export function EmptyState({ icon, title, desc, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center px-4 animate-fade-in">
      <div className="text-5xl mb-4 opacity-50 grayscale">{icon}</div>
      <div className="text-base font-semibold text-text-hi mb-2">{title}</div>
      <div className="text-sm text-text-lo max-w-sm mb-6 leading-relaxed">{desc}</div>
      {action}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// SectionHeader
// ═══════════════════════════════════════════════════════════════════════

interface SectionHeaderProps {
  title:   string
  icon?:   string
  desc?:   string
  action?: ReactNode
}

export function SectionHeader({ title, icon, desc, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div className="border-l-[3px] pl-3" style={{ borderColor: '#22C55E' }}>
        <h2 className="font-semibold text-base text-text-hi tracking-tight">
          {icon && <span className="mr-1.5">{icon}</span>}
          {title}
        </h2>
        {desc && <p className="text-xs text-muted mt-0.5">{desc}</p>}
      </div>
      {action && <div className="ml-4 shrink-0">{action}</div>}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// ChangeIndicator — zmiana procentowa (premium fintech style)
// ═══════════════════════════════════════════════════════════════════════

export function ChangeIndicator({
  value,
  suffix   = '%',
  decimals = 2,
  size     = 'sm',
  pill     = false,
}: {
  value:     number
  suffix?:   string
  decimals?: number
  size?:     'xs' | 'sm' | 'md'
  pill?:     boolean
}) {
  const positive = value >= 0
  const color    = positive ? '#22C55E' : '#EF4444'
  const sizeClass = { xs: 'text-xs', sm: 'text-sm', md: 'text-base' }[size]

  if (pill) {
    return (
      <span
        className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-semibold font-mono tabular-nums', sizeClass)}
        style={{ color, background: positive ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)' }}
      >
        <span className="text-[0.7em]">{positive ? '▲' : '▼'}</span>
        {Math.abs(value).toFixed(decimals)}{suffix}
      </span>
    )
  }

  return (
    <span className={clsx('inline-flex items-center gap-1 font-semibold font-mono tabular-nums', sizeClass)}
      style={{ color }}>
      <span className="text-[0.7em]">{positive ? '▲' : '▼'}</span>
      {Math.abs(value).toFixed(decimals)}{suffix}
    </span>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Stat — KPI tile z akcentem
// ═══════════════════════════════════════════════════════════════════════

export function Stat({
  label,
  value,
  sub,
  color = '#22C55E',
  mono  = true,
}: {
  label: string
  value: string
  sub?:  string
  color?: string
  mono?: boolean
}) {
  return (
    <div className="stat-tile" style={{ '--accent-green': color } as React.CSSProperties}>
      <div className="text-2xs uppercase tracking-widest text-muted mb-1.5">{label}</div>
      <div className={clsx('text-2xl font-bold tabular-nums', mono && 'font-mono')} style={{ color }}>
        {value}
      </div>
      {sub && <div className="text-2xs text-muted mt-1">{sub}</div>}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Price — sformatowana cena z walutą (mono)
// ═══════════════════════════════════════════════════════════════════════

export function Price({
  value,
  currency = '',
  decimals = 2,
  className,
}: {
  value:     number
  currency?: string
  decimals?: number
  className?: string
}) {
  return (
    <span className={clsx('font-mono tabular-nums', className)}>
      {value.toLocaleString('pl-PL', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {currency && <span className="text-muted ml-1 text-[0.85em]">{currency}</span>}
    </span>
  )
}
