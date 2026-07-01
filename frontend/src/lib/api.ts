/**
 * StockFlow API Client
 * Typowany klient HTTP dla backendu FastAPI.
 * Używa axios z automatycznym dodawaniem tokenu JWT.
 */

import axios, { AxiosError, AxiosInstance } from 'axios'

// ── Types ─────────────────────────────────────────────────────────────

export interface ComponentItem {
  key:    string
  score:  number
  note:   string
  weight: number
}

export interface AnalysisResult {
  ticker:       string
  name:         string
  price:        number
  currency:     string
  change_24h:   number | null
  change_pct:   number | null
  total_score:  number
  score_st:     number | null
  asset_type:   string
  sector:       string | null
  industry:     string | null
  components:   ComponentItem[]
  components_st: ComponentItem[]
  red_flags:    string[]
  vwap:         Record<string, unknown> | null
  ma_crossover: Record<string, unknown> | null
  beta_info:    Record<string, unknown> | null
  relative_strength: Record<string, unknown> | null
}

export interface OHLCVCandle {
  timestamp: string
  open:      number
  high:      number
  low:       number
  close:     number
  volume:    number
  bb_upper?:  number | null
  bb_middle?: number | null
  bb_lower?:  number | null
  ma20?:      number | null
  ma50?:      number | null
  ma200?:     number | null
}

export interface MarketData {
  ticker:   string
  interval: string
  source:   string
  candles:  OHLCVCandle[]
  is_live:  boolean
}

export interface WatchlistItem {
  ticker:           string
  last_score:       number | null
  alert_high:       number | null
  alert_low:        number | null
  alert_crossover:  boolean
  added_at:         string | null
}

export interface PositionItem {
  id:            number
  ticker:        string
  name:          string
  shares:        number
  buy_price:     number
  current_price: number
  current_value: number
  pnl:           number
  pnl_pct:       number
  currency:      string
  sector:        string
  buy_date:      string | null
  notes:         string | null
  score:         number | null
}

export interface Portfolio {
  positions:             PositionItem[]
  total_value:           number
  total_pnl:             number
  total_pnl_pct:         number
  allocation_by_sector:  Record<string, number>
  warnings:              string[]
}

export interface JournalEntry {
  id:         number
  entry_date: string
  ticker:     string
  decision:   string
  reason:     string
  score:      number | null
  price:      number | null
  created_at: string | null
}

export interface ScanResultItem {
  ticker:   string
  name:     string | null
  sector:   string | null
  price:    number | null
  score:    number
  score_st: number | null
}

export interface ScanResponse {
  results:    ScanResultItem[]
  scanned_at: string
  total:      number
}

export interface SignalData {
  ticker:     string
  atr:        Record<string, unknown> | null
  stochastic: {
    k:         number
    d:         number
    signal:    string
    crossed:   string
    k_series:  { date: string; value: number }[]
    d_series:  { date: string; value: number }[]
  }
  obv: {
    divergence: Record<string, unknown> | null
    series:     { date: string; value: number }[]
  }
  levels: {
    support:    number[]
    resistance: number[]
  }
}

export interface TokenResponse {
  access_token: string
  token_type:   string
  expires_in:   number
  user_id:      string
}

export type Interval = '1m' | '5m' | '15m' | '30m' | '1h' | '1d'
export type Market   = 'usa' | 'gpw' | 'europa' | 'krypto' | 'all'


// ── API Error ─────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status:  number,
    public detail:  string,
    public code?:   string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}


// ── Client factory ────────────────────────────────────────────────────

function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/api/v1',
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  })

  // Request interceptor — dodaj JWT token
  instance.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('sf_token')
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`
      }
      // Przekaż język do backendu
      const locale = document.cookie
        .split(';')
        .find(c => c.trim().startsWith('locale='))
        ?.split('=')?.[1] ?? 'pl'
      config.headers['Accept-Language'] = locale
    }
    return config
  })

  // Response interceptor — normalizuj błędy
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<{ detail: unknown }>) => {
      const status = error.response?.status ?? 0

      // Wyciągnij czytelny komunikat błędu
      let detail: string
      const rawDetail = error.response?.data?.detail

      if (status === 0) {
        // Brak odpowiedzi — błąd sieci, timeout, serwer niedostępny
        detail = error.code === 'ECONNABORTED'
          ? 'Przekroczono czas oczekiwania. Serwer może się wybudzać — spróbuj ponownie za chwilę.'
          : 'Nie można połączyć się z serwerem. Sprawdź połączenie lub spróbuj ponownie za chwilę.'
      } else if (status >= 500) {
        detail = 'Serwer napotkał błąd. Spróbuj ponownie za chwilę.'
      } else if (Array.isArray(rawDetail)) {
        // 422 z Pydantic — detail to tablica obiektów {loc, msg, type}
        const first = rawDetail[0] as { msg?: string } | undefined
        detail = first?.msg ?? 'Nieprawidłowe dane wejściowe.'
      } else if (typeof rawDetail === 'string') {
        detail = rawDetail
      } else {
        detail = error.message || 'Wystąpił nieoczekiwany błąd.'
      }

      // Auto-logout przy 401 (poza endpointami auth)
      if (status === 401 && typeof window !== 'undefined') {
        const isAuthEndpoint = error.config?.url?.includes('/auth/')
        if (!isAuthEndpoint) {
          localStorage.removeItem('sf_token')
          localStorage.removeItem('sf_user')
          window.dispatchEvent(new Event('sf:logout'))
        }
      }

      throw new ApiError(status, detail)
    },
  )

  return instance
}

const api = createApiClient()


// ── Auth endpoints ────────────────────────────────────────────────────

export const authApi = {
  register: async (username: string, password: string, email?: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/register', {
      username, password, email,
    })
    return data
  },

  login: async (username: string, password: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/login', {
      username, password,
    })
    return data
  },

  me: async (): Promise<{ user_id: string }> => {
    const { data } = await api.get('/auth/me')
    return data
  },
}


// ── Analysis endpoints ────────────────────────────────────────────────

export const analysisApi = {
  search: async (q: string, limit = 8): Promise<{ symbol: string; name: string }[]> => {
    const { data } = await api.get('/analyze/search', { params: { q, limit } })
    return data
  },

  analyze: async (ticker: string): Promise<AnalysisResult> => {
    const { data } = await api.get<AnalysisResult>(`/analyze/${ticker}`)
    return data
  },

  history: async (ticker: string, days = 90): Promise<{ date: string; score: number }[]> => {
    const { data } = await api.get(`/analyze/${ticker}/history`, { params: { days } })
    return data
  },

  signals: async (ticker: string, period = '1y'): Promise<SignalData> => {
    const { data } = await api.get<SignalData>(`/analyze/${ticker}/signals`, {
      params: { period },
    })
    return data
  },

  candles: async (ticker: string, interval: Interval = '1d', overlays = true): Promise<MarketData> => {
    const { data } = await api.get<MarketData>(`/analyze/${ticker}/candles`, {
      params: { interval, overlays },
    })
    return data
  },
}


// ── Watchlist endpoints ────────────────────────────────────────────────

export const watchlistApi = {
  get: async (): Promise<WatchlistItem[]> => {
    const { data } = await api.get<WatchlistItem[]>('/watchlist')
    return data
  },

  add: async (ticker: string): Promise<void> => {
    await api.post('/watchlist', { ticker })
  },

  remove: async (ticker: string): Promise<void> => {
    await api.delete(`/watchlist/${ticker}`)
  },

  setAlerts: async (
    ticker: string,
    alerts: { alert_high?: number; alert_low?: number; alert_crossover?: boolean },
  ): Promise<void> => {
    await api.put(`/watchlist/${ticker}/alerts`, alerts)
  },
}


// ── Portfolio endpoints ────────────────────────────────────────────────

export const portfolioApi = {
  get: async (): Promise<Portfolio> => {
    const { data } = await api.get<Portfolio>('/portfolio')
    return data
  },

  addPosition: async (position: {
    ticker:    string
    shares:    number
    buy_price: number
    buy_date?: string
    notes?:    string
  }): Promise<void> => {
    await api.post('/portfolio', position)
  },

  removePosition: async (id: number): Promise<void> => {
    await api.delete(`/portfolio/${id}`)
  },
}


// ── Journal endpoints ─────────────────────────────────────────────────

export const journalApi = {
  get: async (ticker?: string): Promise<JournalEntry[]> => {
    const { data } = await api.get<JournalEntry[]>('/journal', {
      params: ticker ? { ticker } : {},
    })
    return data
  },

  add: async (entry: {
    entry_date: string
    ticker:     string
    decision:   string
    reason:     string
    score?:     number
    price?:     number
  }): Promise<void> => {
    await api.post('/journal', entry)
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/journal/${id}`)
  },
}


// ── Scanner endpoints ─────────────────────────────────────────────────

export const scannerApi = {
  getResults: async (): Promise<ScanResponse> => {
    const { data } = await api.get<ScanResponse>('/scan')
    return data
  },

  startScan: async (market: Market): Promise<{ message: string; tickers: number }> => {
    const { data } = await api.post('/scan', { market })
    return data
  },

  getStatus: async (): Promise<{
    running:   boolean
    progress:  number
    total:     number
    percent:   number
    current:   string
    elapsed_s: number | null
  }> => {
    const { data } = await api.get('/scan/status')
    return data
  },
}


export interface ForecastData {
  ticker:  string
  horizon: number
  monte_carlo: {
    dates:       string[]
    percentiles: { '5': number[]; '25': number[]; '50': number[]; '75': number[]; '95': number[] }
    stats: {
      current_price:         number
      mu_annualized_pct:     number
      sigma_annualized_pct:  number
      prob_up_pct:           number
      median_final:          number
      p5_final:              number
      p95_final:             number
      horizon_days:          number
    }
  }
  trend: {
    dates:    string[]
    forecast: number[]
    lower_90: number[]
    upper_90: number[]
    slope_pct_per_day: number
  } | null
  interpretation: string
}

export const forecastApi = {
  get: async (ticker: string, horizon = 30): Promise<ForecastData> => {
    const { data } = await api.get<ForecastData>(`/forecast/${ticker}`, {
      params: { horizon },
    })
    return data
  },
}


export interface NewsItem {
  title:     string
  link:      string
  publisher: string
  published: string
}

export const newsApi = {
  get: async (ticker: string, limit = 8): Promise<NewsItem[]> => {
    const { data } = await api.get<{ news: NewsItem[] }>(`/news/${ticker}`, {
      params: { limit },
    })
    return data.news
  },
}


export interface BacktestResult {
  ticker:         string
  period:         string
  buy_threshold:  number
  sell_threshold: number
  equity_curve:   { date: string; strategy: number; buyhold: number }[]
  trades: {
    entry_date:  string
    exit_date:   string
    entry_price: number
    exit_price:  number
    return_pct:  number
    still_open:  boolean
  }[]
  metrics: {
    total_return:        number
    buyhold_return:      number
    num_trades:          number
    win_rate:            number
    max_drawdown:        number
    final_value:         number
    buyhold_final_value: number
    sharpe:              number
    sortino:             number
    still_open:          boolean
  }
}

export interface GridResult {
  ticker:         string
  cells:          { buy: number; sell: number; return: number }[]
  best:           { buy: number; sell: number; return: number }
  buyhold_return: number
}

export interface WalkForwardResult {
  ticker:  string
  windows: {
    okres_od:           string
    okres_do:           string
    'strategia_%':      number
    'kup_i_trzymaj_%':  number
    lepsza_niz_bh:      boolean
    liczba_transakcji:  number
    'max_obsuniecie_%': number
  }[]
  summary: { n_windows: number; wins: number; win_rate_pct: number }
}

export const backtestApi = {
  run: async (ticker: string, opts: {
    period?: string; buy?: number; sell?: number; capital?: number
  } = {}): Promise<BacktestResult> => {
    const { data } = await api.get<BacktestResult>(`/backtest/${ticker}`, {
      params: {
        period: opts.period ?? '2y',
        buy_threshold: opts.buy ?? 65,
        sell_threshold: opts.sell ?? 35,
        initial_capital: opts.capital ?? 10000,
      },
    })
    return data
  },
  grid: async (ticker: string, period = '2y'): Promise<GridResult> => {
    const { data } = await api.get<GridResult>(`/backtest/${ticker}/grid`, {
      params: { period },
    })
    return data
  },
  walkForward: async (ticker: string, opts: {
    period?: string; buy?: number; sell?: number; windows?: number
  } = {}): Promise<WalkForwardResult> => {
    const { data } = await api.get<WalkForwardResult>(`/backtest/${ticker}/walkforward`, {
      params: {
        period: opts.period ?? '5y',
        buy_threshold: opts.buy ?? 65,
        sell_threshold: opts.sell ?? 35,
        n_windows: opts.windows ?? 4,
      },
    })
    return data
  },
}


export default api
