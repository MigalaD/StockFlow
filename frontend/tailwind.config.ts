import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // ── StockFlow Brand Tokens ──────────────────────────────────────
      colors: {
        brand: {
          green:   '#22C55E',
          'green-dark': '#16A34A',
          teal:    '#14B8A6',
          blue:    '#3B82F6',
        },
        surface: {
          DEFAULT: '#111827',   // karty, sidebar
          hi:      '#1E293B',   // hover states
          lo:      '#0B1120',   // główne tło
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.07)',
          hi:      'rgba(255,255,255,0.12)',
        },
        score: {
          positive: '#22C55E',
          neutral:  '#F59E0B',
          negative: '#EF4444',
        },
      },

      // ── Typography ─────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      fontVariantNumeric: {
        'tabular':  'tabular-nums',
      },

      // ── Spacing ────────────────────────────────────────────────────
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },

      // ── Border radius ──────────────────────────────────────────────
      borderRadius: {
        'xl2': '14px',
        'xl3': '18px',
      },

      // ── Animations ─────────────────────────────────────────────────
      animation: {
        'ticker':     'ticker 28s linear infinite',
        'fade-in':    'fadeIn 0.18s ease-in',
        'slide-up':   'slideUp 0.2s ease-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
      keyframes: {
        ticker: {
          from: { transform: 'translateX(0)' },
          to:   { transform: 'translateX(-50%)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },

      // ── Shadows ────────────────────────────────────────────────────
      boxShadow: {
        'card':  '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'green': '0 0 20px rgba(34,197,94,0.15)',
      },

      // ── Background ─────────────────────────────────────────────────
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #22C55E, #16A34A)',
        'teal-gradient':  'linear-gradient(135deg, #14B8A6, #0D9488)',
        'card-gradient':  'linear-gradient(145deg, #111827, #0F172A)',
      },
    },
  },
  plugins: [],
}

export default config
