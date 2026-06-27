# StockFlow — Przewodnik migracji do Next.js + FastAPI

## Architektura docelowa

```
┌─────────────────┐     HTTPS      ┌────────────────────┐
│  Next.js (Vercel)│ ──────────► │ FastAPI (Railway)   │
│  stockflow.app   │              │ api.stockflow.app    │
│  PL / EN        │              │ /api/v1/...          │
└─────────────────┘              └────────┬───────────┘
                                          │
                                 ┌────────▼───────────┐
                                 │  Supabase (Postgres) │
                                 │  auth + dane users   │
                                 └─────────────────────┘
```

Streamlit Cloud pozostaje na produkcji do czasu ukończenia migracji.

---

## Krok 1 — FastAPI backend (GOTOWE ✅)

### Lokalnie
```bash
# Z katalogu głównego projektu (tam gdzie jest stock_analyzer.py)
pip install -r requirements-backend.txt

cp backend/.env.example backend/.env
# Uzupełnij SECRET_KEY: openssl rand -hex 32

uvicorn backend.main:app --reload --port 8000
# Dokumentacja: http://localhost:8000/docs
```

### Testy backendu
```bash
pytest backend/tests/ -v
```

### Deploy na Railway
1. Zaloguj się na railway.app
2. New Project → Deploy from GitHub repo → wybierz `stockflow`
3. W zakładce Variables ustaw:
   ```
   SECRET_KEY=<openssl rand -hex 32>
   ENVIRONMENT=production
   ALLOWED_ORIGINS=https://twoja-domena.vercel.app
   ```
4. Railway wykryje `Procfile` automatycznie

---

## Krok 2 — Supabase (baza danych)

### Założenie projektu
1. Wejdź na supabase.com → New project
2. Zapamiętaj hasło bazy
3. Settings → Database → Connection string (URI) → skopiuj

### Konfiguracja
```bash
# W backend/.env dodaj:
DATABASE_URL=postgresql://postgres:[HASLO]@db.[PROJEKT].supabase.co:5432/postgres
```

### Migracja danych ze Streamlit (jednorazowa)
```bash
# Pobierz stock_app.db ze Streamlit Cloud (Manage App → Files)
python -m backend.core.database ./stock_app.db
```

Skrypt przeniesie: watchlist, portfolio, journal, score_history, scan_results.

---

## Krok 3 — Next.js frontend

### Lokalnie
```bash
cd frontend
cp .env.local.example .env.local
# Ustaw NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
# http://localhost:3000
```

### Deploy na Vercel
1. Wejdź na vercel.com → New Project → Import z GitHub
2. Framework: Next.js (auto-detect)
3. Root Directory: `frontend`
4. Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://[twoj-projekt].up.railway.app
   ```
5. Deploy

---

## Zmienne środowiskowe — podsumowanie

### Backend (Railway)
| Zmienna | Wymagana | Opis |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing key (openssl rand -hex 32) |
| `ENVIRONMENT` | ✅ | `production` |
| `DATABASE_URL` | ✅ | Supabase PostgreSQL URL |
| `ALLOWED_ORIGINS` | ✅ | URL frontendu Vercel (CORS) |
| `ALPACA_API_KEY` | ❌ | Live ceny akcji USA (opcjonalne) |
| `ALPACA_SECRET_KEY` | ❌ | j.w. |

### Frontend (Vercel)
| Zmienna | Wymagana | Opis |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | URL backendu Railway |

---

## i18n — obsługa języków

Tłumaczenia w:
- `frontend/src/messages/pl.json` — polski (domyślny)
- `frontend/src/messages/en.json` — angielski

Użytkownik zmienia język w Ustawieniach → LanguageSwitcher zapisuje
wybór w cookie `locale` → next-intl czyta przy każdym żądaniu.

Dodanie nowego języka:
1. Utwórz `frontend/src/messages/[kod].json`
2. Dodaj kod do `locales` w `frontend/src/i18n/request.ts`
3. Dodaj opcję w LanguageSwitcher

---

## Struktura plików

```
stockflow/
├── backend/                    ← FastAPI (Python)
│   ├── main.py                 ← Entry point (uvicorn)
│   ├── core/
│   │   ├── config.py           ← Settings z env vars
│   │   ├── security.py         ← JWT auth
│   │   └── database.py         ← SQLite/PostgreSQL abstraction
│   ├── models/
│   │   └── schemas.py          ← Pydantic models
│   ├── routers/
│   │   ├── auth.py             ← /auth/*
│   │   ├── analysis.py         ← /analyze/*
│   │   ├── watchlist.py        ← /watchlist/*
│   │   ├── portfolio.py        ← /portfolio/*
│   │   └── scanner_journal.py  ← /scan/*, /journal/*
│   └── tests/
│       └── test_api.py         ← 30+ testów
│
├── frontend/                   ← Next.js 14 (TypeScript)
│   ├── src/
│   │   ├── app/                ← App Router pages
│   │   ├── components/         ← React components
│   │   ├── lib/api.ts          ← Typowany klient API
│   │   ├── store/index.ts      ← Zustand (auth, settings, recent)
│   │   ├── i18n/               ← next-intl config
│   │   └── messages/           ← pl.json, en.json
│   ├── package.json
│   ├── tailwind.config.ts      ← Brand tokens
│   └── vercel.json
│
├── Procfile                    ← Railway deployment
├── railway.toml                ← Railway config
├── requirements-backend.txt    ← FastAPI deps
│
├── stock_analyzer.py           ← Istniejący kod (współdzielony)
├── database.py                 ← Istniejący kod + tabela users
└── ... (reszta Streamlit)
```

---

## Kolejność wdrożenia

```
Teraz:  backend lokalne testy → Railway deploy → Supabase setup
Potem:  Next.js pages (Dashboard, Analiza, Watchlist, Portfolio)
Potem:  Scanner, Backtest, Settings, Auth UI
Finał:  Przeniesienie ruchu ze Streamlit na Next.js
```

Streamlit Cloud pozostaje aktywny przez całą migrację.
