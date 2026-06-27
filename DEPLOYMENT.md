# StockFlow — Kompletny Przewodnik Wdrożenia

## Struktura projektu (jak rozmieścić pliki)

```
stockflow/                          ← GŁÓWNY KATALOG (ten sam co teraz na GitHub)
│
├── App.py                          ← Streamlit — strona główna (dashboard)
├── requirements.txt                ← Zależności Streamlit (nie zmieniaj)
├── requirements-backend.txt        ← Zależności FastAPI (nowe)
├── Procfile                        ← Railway — komenda startowa
├── railway.toml                    ← Railway — konfiguracja deploymentu
├── CHANGELOG.md
├── MIGRATION.md
├── LICENSE
│
├── .streamlit/
│   └── config.toml                 ← Brand colors, dark theme
│
├── pages/                          ← Strony Streamlit (z emoji w nazwach)
│   ├── 1_📈_Analiza.py
│   ├── 2_🔀_Porownanie.py
│   ├── 3_⭐_Watchlist.py
│   ├── 4_💼_Portfolio.py
│   ├── 5_🚀_Wzrostowe.py
│   ├── 6_📦_ETF.py
│   ├── 6b_₿_Krypto.py
│   ├── 7_📓_Dziennik.py
│   ├── 8_🔍_Skaner.py
│   ├── 9_🧪_Backtest.py
│   ├── 10_⚙️_Ustawienia.py
│   └── 11_ℹ️_O_aplikacji.py
│
├── pages_clean/                    ← Kopie stron bez emoji (dla niektórych hostingów)
│   └── *.py
│
├── common.py                       ← Współdzielone funkcje Streamlit
├── stock_analyzer.py               ← Silnik analizy (DT scoring)
├── intraday_signals.py             ← Sygnały ST (ATR, Stochastik, OBV)
├── database.py                     ← SQLite + PostgreSQL abstraction
├── scanner.py                      ← Skaner rynku
├── portfolio.py                    ← Analiza portfolio
├── external_data.py                ← Binance, CoinGecko, Alpaca
├── tickers.py                      ← Listy tickerów (USA, GPW, Krypto...)
│
├── backend/                        ← FastAPI (nowe — nie koliduje ze Streamlit)
│   ├── __init__.py
│   ├── main.py                     ← Entry point: uvicorn backend.main:app
│   ├── scheduler.py                ← Alert scheduler (Telegram/email)
│   ├── .env.example                ← Skopiuj do .env i uzupełnij
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               ← Zmienne środowiskowe
│   │   ├── security.py             ← JWT, bcrypt
│   │   └── database.py             ← Warstwa abstrakcji SQLite/PostgreSQL
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py              ← Pydantic modele
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                 ← POST /auth/register, /login
│   │   ├── analysis.py             ← GET /analyze/{ticker}
│   │   ├── watchlist.py            ← CRUD /watchlist
│   │   ├── portfolio.py            ← CRUD /portfolio
│   │   ├── pdf.py                  ← GET /pdf/{ticker}
│   │   └── scanner_journal.py      ← /scan, /journal
│   └── tests/
│       ├── __init__.py
│       └── test_api.py             ← 30+ testów pytest
│
└── frontend/                       ← Next.js 14 (nowe — osobne repozytorium lub subfolder)
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── postcss.config.js
    ├── vercel.json
    ├── .eslintrc.json
    ├── .env.local.example          ← Skopiuj do .env.local
    ├── public/
    │   └── manifest.json           ← PWA manifest
    └── src/
        ├── app/                    ← Next.js App Router — 13 stron
        │   ├── layout.tsx
        │   ├── page.tsx            ← Dashboard (/)
        │   ├── login/page.tsx
        │   ├── analysis/page.tsx
        │   ├── compare/page.tsx
        │   ├── watchlist/page.tsx
        │   ├── portfolio/page.tsx
        │   ├── crypto/page.tsx
        │   ├── scanner/page.tsx
        │   ├── backtest/page.tsx
        │   ├── journal/page.tsx
        │   ├── settings/page.tsx
        │   ├── about/page.tsx
        │   └── styles/globals.css
        ├── components/
        │   ├── ui/
        │   │   ├── ScoreBadge.tsx
        │   │   └── index.tsx       ← Card, Button, Input, Tag, Spinner...
        │   ├── layout/
        │   │   ├── AppShell.tsx
        │   │   ├── Sidebar.tsx
        │   │   └── TickerTape.tsx
        │   └── shared/
        │       ├── AuthGuard.tsx
        │       ├── LanguageSwitcher.tsx
        │       └── ToastProvider.tsx
        ├── lib/
        │   └── api.ts              ← Typowany klient HTTP
        ├── store/
        │   └── index.ts            ← Zustand (auth, settings, recent)
        ├── i18n/
        │   └── request.ts
        └── messages/
            ├── pl.json             ← Tłumaczenia PL
            └── en.json             ← Tłumaczenia EN
```

---

## KROK 1 — Przygotowanie repo lokalnie

```bash
# Wejdź do katalogu projektu (tam gdzie jest App.py)
cd ~/stockflow

# Sprawdź że masz Python 3.11+
python3 --version

# Utwórz .env dla backendu
cp backend/.env.example backend/.env
```

Otwórz `backend/.env` i uzupełnij:
```env
SECRET_KEY=<wynik poniższej komendy>
ENVIRONMENT=development
```

Wygeneruj SECRET_KEY:
```bash
openssl rand -hex 32
# Skopiuj wynik i wklej jako SECRET_KEY w .env
```

---

## KROK 2 — Lokalny test backendu FastAPI

```bash
# Zainstaluj zależności backendu
pip install -r requirements-backend.txt

# Uruchom serwer
uvicorn backend.main:app --reload --port 8000

# Powinieneś zobaczyć:
# ✅ SQLite connected (./stock_app.db)
# ✅ StockFlow API v1.1.0 started
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

Otwórz **http://localhost:8000/docs** — zobaczysz Swagger UI ze wszystkimi endpointami.

Przetestuj rejestrację:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"haslo1234"}'
# Powinien zwrócić: {"access_token":"eyJ...","user_id":"test"}
```

Uruchom testy:
```bash
pytest backend/tests/ -v
# Oczekiwane: 30+ testów, wszystkie zielone
```

---

## KROK 3 — Lokalny test frontendu Next.js

```bash
# Wejdź do katalogu frontendu
cd frontend

# Utwórz .env.local
cp .env.local.example .env.local
# Zawartość: NEXT_PUBLIC_API_URL=http://localhost:8000

# Zainstaluj zależności Node.js
npm install

# Uruchom serwer deweloperski
npm run dev

# Otwórz http://localhost:3000
```

Na ekranie powinieneś zobaczyć aplikację z:
- Ticker tape na górze (przewijające się ceny)
- Sidebar z nawigacją
- Dashboard ze statystykami

---

## KROK 4 — Założenie konta Supabase (baza produkcyjna)

1. Wejdź na **https://supabase.com** → Sign Up (bezpłatny plan wystarczy)
2. Kliknij **New project**
   - Organization: Twoja organizacja (lub utwórz nową)
   - Name: `stockflow`
   - Database Password: **zapisz to hasło!**
   - Region: **West EU (Frankfurt)** — najbliżej Polski
3. Poczekaj ~2 minuty na inicjalizację projektu
4. Przejdź do **Settings → Database → Connection string → URI**
5. Skopiuj URL w formacie:
   ```
   postgresql://postgres:[TWOJE_HASŁO]@db.[PROJEKT_ID].supabase.co:5432/postgres
   ```

---

## KROK 5 — Migracja danych SQLite → Supabase

```bash
# W katalogu głównym projektu (stockflow/)

# Dodaj DATABASE_URL do backend/.env
echo 'DATABASE_URL=postgresql://postgres:[HASŁO]@db.[PROJEKT].supabase.co:5432/postgres' >> backend/.env

# Uruchom skrypt migracji (jednorazowo)
python -m backend.core.database ./stock_app.db

# Powinieneś zobaczyć:
# Migracja: ./stock_app.db → PostgreSQL (postgresql://...)
# Wynik migracji:
#   watchlist           :    X rekordów
#   portfolio           :    X rekordów
#   journal             :    X rekordów
#   ...
```

Jeśli nie masz istniejącej bazy (nowy projekt):
```bash
# Pomiń migrację — tabele zostaną utworzone automatycznie przy starcie API
uvicorn backend.main:app --reload --port 8000
```

---

## KROK 6 — Deploy backendu na Railway

1. Wejdź na **https://railway.app** → Login z GitHub
2. Kliknij **New Project → Deploy from GitHub repo**
3. Wybierz repozytorium `stockflow` (lub `migalad/stockflow`)
4. Railway automatycznie wykryje `Procfile`

**Ustaw zmienne środowiskowe** (zakładka Variables):

| Zmienna | Wartość |
|---|---|
| `SECRET_KEY` | Ten sam co w backend/.env (openssl rand -hex 32) |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Connection string z Supabase |
| `ALLOWED_ORIGINS` | `https://stockflow.vercel.app` (ustaw po deploy Vercel) |
| `LOG_LEVEL` | `INFO` |

5. Kliknij **Deploy** — Railway zbuduje i uruchomi aplikację
6. Skopiuj URL deploymentu (np. `https://stockflow-api.up.railway.app`)
7. Sprawdź: `https://[TWOJ_URL]/health` — powinien zwrócić `{"status":"ok",...}`

**Włącz Cron Job dla alertów** (opcjonalnie, plan Hobby+):
```toml
# Odkomentuj w railway.toml:
[cron]
schedule = "*/30 * * * *"
command  = "python -m backend.scheduler"
```

---

## KROK 7 — Deploy frontendu na Vercel

1. Wejdź na **https://vercel.com** → Login z GitHub
2. Kliknij **New Project → Import Git Repository**
3. Wybierz repozytorium `stockflow`
4. **Root Directory**: ustaw na `frontend`
5. Framework: **Next.js** (auto-detect)
6. **Environment Variables** (kliknij Add):

| Zmienna | Wartość |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL backendu z Railway (np. `https://stockflow-api.up.railway.app`) |

7. Kliknij **Deploy**
8. Skopiuj URL (np. `https://stockflow.vercel.app`)

**Wróć do Railway** i zaktualizuj `ALLOWED_ORIGINS`:
```
https://stockflow.vercel.app
```

---

## KROK 8 — Weryfikacja wdrożenia

Otwórz `https://stockflow.vercel.app` i sprawdź kolejno:

```
✅ Strona ładuje się (ciemne tło, ticker tape)
✅ Rejestracja działa (/login → Zarejestruj się)
✅ Login działa
✅ Analiza AAPL zwraca wyniki (/analysis?ticker=AAPL)
✅ Watchlista zapisuje się po odświeżeniu strony
✅ Skaner uruchamia się i pokazuje wyniki
✅ PDF pobiera się (/api/v1/pdf/AAPL)
```

---

## KROK 9 — Aktualizacja Streamlit (opcjonalnie)

Streamlit Cloud pozostaje jako backup. Jeśli chcesz zaktualizować tam też wersję:

```bash
# Na Streamlit Cloud jest gałąź main
git add .
git commit -m "v1.2.0: FastAPI backend + Next.js frontend"
git push origin main
```

Streamlit Cloud automatycznie przebuduje aplikację.

---

## Rozwiązywanie problemów

### Backend nie startuje
```bash
# Sprawdź logi Railway → Deployments → View Logs
# Najczęstsze problemy:

# 1. Brak SECRET_KEY
ERROR: SECRET_KEY nie ustawiony → dodaj zmienną w Railway

# 2. Błąd połączenia z Supabase
ERROR: asyncpg.exceptions.InvalidPasswordError
→ Sprawdź DATABASE_URL (szczególnie hasło — może mieć znaki specjalne, użyj URL-encode)

# 3. Import error
ModuleNotFoundError: No module named 'stock_analyzer'
→ Sprawdź że Procfile uruchamia z katalogu gdzie jest stock_analyzer.py:
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Frontend nie łączy się z backendem
```bash
# Sprawdź w przeglądarce: F12 → Network → błędy CORS lub 404

# 1. CORS error
→ Upewnij się że ALLOWED_ORIGINS w Railway zawiera dokładny URL Vercel
→ Bez trailing slash: https://stockflow.vercel.app (NIE https://stockflow.vercel.app/)

# 2. 404 na wszystkich endpointach
→ Sprawdź NEXT_PUBLIC_API_URL w Vercel — musi być bez /api/v1 na końcu

# 3. "Network Error" w przeglądarce
→ Railway może być uśpiony (darmowy plan) — otwórz /health żeby go obudzić
```

### Baza danych
```bash
# Sprawdź tabele w Supabase → Table Editor
# Powinny istnieć: users, watchlist, portfolio, journal, scan_results, score_history

# Jeśli tabel nie ma — restart API wystarczy (init_db() tworzy je automatycznie)
```

---

## Komendy szybkiego dostępu

```bash
# Lokalny development
uvicorn backend.main:app --reload --port 8000    # Backend FastAPI
cd frontend && npm run dev                        # Frontend Next.js

# Testy
pytest backend/tests/ -v                          # Testy API
pytest backend/tests/ -v -k "test_auth"           # Tylko testy auth

# Scheduler alertów (manualnie)
python -m backend.scheduler                        # Jednorazowo
python -m backend.scheduler --loop --interval 30  # Pętla co 30 min

# Migracja bazy
python -m backend.core.database ./stock_app.db    # SQLite → PostgreSQL

# Build produkcyjny frontendu
cd frontend && npm run build && npm run start
```

---

## Zmienne środowiskowe — kompletna lista

### Backend (Railway / local backend/.env)
```env
# Wymagane
SECRET_KEY=<openssl rand -hex 32>
ENVIRONMENT=production
DATABASE_URL=postgresql://postgres:[HASŁO]@db.[PROJEKT].supabase.co:5432/postgres
ALLOWED_ORIGINS=https://[TWOJA_DOMENA].vercel.app

# Opcjonalne
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ANALYSIS_CACHE_TTL=900
SCAN_CACHE_TTL=3600
YF_RATE_LIMIT=4
LOG_LEVEL=INFO
SCHEDULER_INTERVAL_MINUTES=30
ALPACA_API_KEY=<opcjonalne — live ceny USA>
ALPACA_SECRET_KEY=<opcjonalne>
```

### Frontend (Vercel / local frontend/.env.local)
```env
NEXT_PUBLIC_API_URL=https://[TWOJ_PROJEKT].up.railway.app
```

---

## Endpointy API — ściągawka

```
GET  /                              → info o API
GET  /health                        → status (db, źródła danych)
GET  /docs                          → Swagger UI

POST /api/v1/auth/register          → rejestracja
POST /api/v1/auth/login             → login → JWT token
GET  /api/v1/auth/me                → profil (wymaga JWT)

GET  /api/v1/analyze/search?q=AAPL  → wyszukiwanie
GET  /api/v1/analyze/{ticker}        → pełna analiza
GET  /api/v1/analyze/{ticker}/history → historia score
GET  /api/v1/analyze/{ticker}/signals → sygnały ST
GET  /api/v1/analyze/{ticker}/candles → dane OHLCV

GET  /api/v1/watchlist              → pobierz (JWT)
POST /api/v1/watchlist              → dodaj (JWT)
DELETE /api/v1/watchlist/{ticker}   → usuń (JWT)
PUT  /api/v1/watchlist/{ticker}/alerts → alerty (JWT)

GET  /api/v1/portfolio              → portfolio z P&L (JWT)
POST /api/v1/portfolio              → dodaj pozycję (JWT)
DELETE /api/v1/portfolio/{id}       → usuń pozycję (JWT)

GET  /api/v1/journal                → wpisy (JWT)
POST /api/v1/journal                → nowy wpis (JWT)
DELETE /api/v1/journal/{id}         → usuń wpis (JWT)

GET  /api/v1/scan                   → wyniki skanu (publiczny)
POST /api/v1/scan                   → uruchom skan (JWT)
GET  /api/v1/scan/status            → postęp skanu

GET  /api/v1/pdf/{ticker}           → raport PDF (publiczny)
```
