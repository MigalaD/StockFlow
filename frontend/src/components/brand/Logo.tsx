import Image from 'next/image'

// Pliki w /public/brand są przycięte do treści. Proporcje liczone z ich
// rzeczywistych wymiarów, żeby next/image nie rozciągał znaku.
const WORDMARK_RATIO = 738 / 120   // stockflow-logo-on-dark.png
const MARK_RATIO     = 105 / 96    // stockflow-mark.png
// Napis zaczyna się po znaku fal: ~24,3% szerokości logo.
export const WORDMARK_TEXT_OFFSET = 0.243

/** Pełne logo (znak + napis) na ciemne tło interfejsu. */
export function Logo({
  height = 28, className = '', priority = false,
}: { height?: number; className?: string; priority?: boolean }) {
  return (
    <Image
      src="/brand/stockflow-logo-on-dark.png"
      alt="Stockflow"
      width={Math.round(height * WORDMARK_RATIO)}
      height={height}
      priority={priority}
      className={className}
    />
  )
}

/** Sam znak fal, np. tam, gdzie nazwa jest już obok. */
export function LogoMark({ size = 20, className = '' }: { size?: number; className?: string }) {
  return (
    <Image
      src="/brand/stockflow-mark.png"
      alt=""
      aria-hidden
      width={Math.round(size * MARK_RATIO)}
      height={size}
      className={className}
    />
  )
}

/** Szerokość logo w px dla danej wysokości (do wyrównania podpisu pod napisem). */
export function wordmarkWidth(height: number): number {
  return Math.round(height * WORDMARK_RATIO)
}
