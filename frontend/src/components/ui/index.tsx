'use client'

import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'
import type { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from 'react'

// ── Card ─────────────────────────────────────────────────────────────

interface CardProps {
  children:   ReactNode
  className?: string
  accent?:    string   // border-left color hex
  padding?:   boolean
}

export function Card({ children, className, accent, padding = true }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-surface border border-border rounded-xl2',
        padding && 'p-4',
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
      'flex items-center justify-between px-4 py-3',
      'border-b border-border',
      className,
    )}>
      <div className="font-semibold text-sm text-white">{children}</div>
      {action && <div>{action}</div>}
    </div>
  )
}


// ── Button ────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:  ButtonVariant
  size?:     'sm' | 'md' | 'lg'
  loading?:  boolean
  icon?:     ReactNode
  children?: ReactNode
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:   'bg-brand-gradient text-white hover:opacity-85',
  secondary: 'border border-brand-green text-brand-green hover:bg-brand-green/10',
  ghost:     'text-muted hover:text-white hover:bg-surface-hi',
  danger:    'border border-red-500 text-red-400 hover:bg-red-500/10',
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
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2',
        'rounded-lg font-semibold transition-all',
        'active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading
        ? <Loader2 className="w-4 h-4 animate-spin" />
        : icon
      }
      {children}
    </button>
  )
}


// ── Input ─────────────────────────────────────────────────────────────

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?:   string
  error?:   string
  hint?:    string
  prefix?:  ReactNode
}

export function Input({ label, error, hint, prefix, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs font-medium text-muted uppercase tracking-wider">
          {label}
        </label>
      )}
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm">
            {prefix}
          </span>
        )}
        <input
          className={clsx(
            'input',
            prefix && 'pl-8',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-500/20',
            className,
          )}
          {...props}
        />
      </div>
      {error && <span className="text-xs text-red-400">{error}</span>}
      {hint && !error && <span className="text-xs text-muted">{hint}</span>}
    </div>
  )
}


// ── Tag ───────────────────────────────────────────────────────────────

interface TagProps {
  children:   ReactNode
  color?:     string
  className?: string
}

export function Tag({ children, color, className }: TagProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded-full',
        'text-xs font-medium border',
        className,
      )}
      style={color ? {
        color,
        borderColor:     color + '50',
        backgroundColor: color + '18',
      } : undefined}
    >
      {children}
    </span>
  )
}


// ── Spinner ───────────────────────────────────────────────────────────

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }[size]
  return (
    <Loader2
      className={clsx('animate-spin text-brand-green', sizeClass)}
    />
  )
}


// ── EmptyState ────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon:      string
  title:     string
  desc:      string
  action?:   ReactNode
}

export function EmptyState({ icon, title, desc, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center px-4">
      <div className="text-5xl mb-4 opacity-60">{icon}</div>
      <div className="text-base font-semibold text-white mb-2">{title}</div>
      <div className="text-sm text-muted max-w-sm mb-5 leading-relaxed">{desc}</div>
      {action}
    </div>
  )
}


// ── SectionHeader ─────────────────────────────────────────────────────

interface SectionHeaderProps {
  title:  string
  icon?:  string
  desc?:  string
  action?: ReactNode
}

export function SectionHeader({ title, icon, desc, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div
        className="border-l-[3px] border-brand-green pl-3 py-0.5"
        style={{ borderColor: '#22C55E' }}
      >
        <h2 className="font-semibold text-base text-white">
          {icon && <span className="mr-1.5">{icon}</span>}
          {title}
        </h2>
        {desc && <p className="text-xs text-muted mt-0.5">{desc}</p>}
      </div>
      {action && <div className="ml-4 shrink-0">{action}</div>}
    </div>
  )
}


// ── ChangeIndicator ───────────────────────────────────────────────────

export function ChangeIndicator({
  value,
  suffix = '%',
  decimals = 2,
}: {
  value:    number
  suffix?:  string
  decimals?: number
}) {
  const positive = value >= 0
  return (
    <span
      className="font-semibold tabular-nums text-sm"
      style={{ color: positive ? '#22C55E' : '#EF4444' }}
    >
      {positive ? '▲' : '▼'} {Math.abs(value).toFixed(decimals)}{suffix}
    </span>
  )
}
