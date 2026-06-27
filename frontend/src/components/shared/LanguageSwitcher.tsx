'use client'

import { useTranslations } from 'next-intl'
import { useSettingsStore } from '../../store'

export function LanguageSwitcher() {
  const t         = useTranslations('settings')
  const { locale, setLocale } = useSettingsStore()

  return (
    <div className="flex items-center gap-1 bg-surface-hi rounded-lg p-0.5">
      {(['pl', 'en'] as const).map((lang) => (
        <button
          key={lang}
          onClick={() => {
            setLocale(lang)
            // Przeładuj stronę żeby next-intl zaktualizował tłumaczenia
            window.location.reload()
          }}
          className="px-2.5 py-1 rounded-md text-xs font-semibold transition-all"
          style={{
            background: locale === lang ? 'rgba(34,197,94,0.2)' : 'transparent',
            color:      locale === lang ? '#22C55E' : '#64748B',
            border:     locale === lang ? '1px solid rgba(34,197,94,0.4)' : '1px solid transparent',
          }}
          aria-label={lang === 'pl' ? 'Polski' : 'English'}
        >
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
