import { getRequestConfig } from 'next-intl/server'
import { cookies, headers } from 'next/headers'

export const locales = ['pl', 'en'] as const
export type Locale = (typeof locales)[number]

function isLocale(v: string | undefined): v is Locale {
  return !!v && (locales as readonly string[]).includes(v)
}

/**
 * Wybór języka:
 * 1. ciasteczko `locale` (świadomy wybór w przełączniku) — zawsze wygrywa,
 * 2. pierwszy obsługiwany język z listy preferencji przeglądarki
 *    (Accept-Language, np. "de-DE,de;q=0.9,en;q=0.8" -> en),
 * 3. polski jako rynek docelowy.
 * Bez punktu 2 każdy nowy gość z zagranicy widział polski landing.
 */
function fromAcceptLanguage(header: string | null): Locale | undefined {
  if (!header) return undefined
  const prefs = header
    .split(',')
    .map(part => {
      const [tag, q] = part.trim().split(';q=')
      return { lang: tag.toLowerCase().split('-')[0], q: q ? parseFloat(q) : 1 }
    })
    .filter(p => p.lang && !Number.isNaN(p.q))
    .sort((a, b) => b.q - a.q)
  return prefs.map(p => p.lang).find(isLocale)
}

export default getRequestConfig(async () => {
  const fromCookie = cookies().get('locale')?.value
  const locale: Locale = isLocale(fromCookie)
    ? fromCookie
    : fromAcceptLanguage(headers().get('accept-language')) ?? 'pl'

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  }
})
