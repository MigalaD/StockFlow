import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          green:   '#22C55E',
          'green-dark': '#16A34A',
          teal:    '#14B8A6',
          blue:    '#3B82F6',
          violet:  '#8B5CF6',
        },
        // Surface elevation scale
        base:    '#080C16',
        sunken:  '#0B1120',
        surface: {
          DEFAULT: '#0F1623',
          1:  '#0F1623',
          2:  '#141C2B',
          3:  '#1C2638',
          hi: '#141C2B',
          lo: '#0B1120',
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.06)',
          hi:      'rgba(255,255,255,0.10)',
        },
        gain:    '#22C55E',
        loss:    '#EF4444',
        // Text scale
        'text-hi':    '#F8FAFC',
        'text-mid':   '#CBD5E1',
        'text-lo':    '#94A3B8',
        muted:        '#64748B',
        score: {
          positive: '#22C55E',
          neutral:  '#F59E0B',
          negative: '#EF4444',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      borderRadius: {
        'xl2': '14px',
        'xl3': '18px',
      },
      boxShadow: {
        'card':  '0 2px 8px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'lg-dark': '0 8px 24px rgba(0,0,0,0.5)',
        'glow':  '0 0 0 1px rgba(34,197,94,0.2), 0 0 20px rgba(34,197,94,0.08)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #22C55E, #16A34A)',
        'teal-gradient':  'linear-gradient(135deg, #14B8A6, #0D9488)',
      },
      animation: {
        'fade-in':   'fadeIn 0.25s ease-out',
        'slide-up':  'slideUp 0.3s cubic-bezier(0.16,1,0.3,1)',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}

export default config
