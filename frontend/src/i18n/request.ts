import { getRequestConfig } from 'next-intl/server'
import { cookies } from 'next/headers'

export const locales = ['pl', 'en'] as const
export type Locale = (typeof locales)[number]

export default getRequestConfig(async () => {
  // Wykryj język z cookie (ustawiany przez LanguageSwitcher)
  // Fallback: 'pl' (główny rynek docelowy)
  const cookieStore = cookies()
  const locale = (cookieStore.get('locale')?.value as Locale) ?? 'pl'

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  }
})
