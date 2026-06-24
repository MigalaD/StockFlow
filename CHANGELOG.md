# Changelog

Wszystkie znaczące zmiany w Analizatorze Spółek są dokumentowane w tym pliku.

Format luźno wzorowany na [Keep a Changelog](https://keepachangelog.com/).
Wersjonowanie: [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

---

## [1.1.0] — 2026-06-20

### Dodano

**Scoring krypto i surowców — pełna separacja**
- Kryptowaluty mają teraz własny `asset_type="crypto"`, osobny od surowców
  (wcześniej traktowane identycznie pod wspólnym `"commodity"`).
- `score_volatility_crypto()` — progi zmienności kalibrowane pod realia rynku
  krypto (50–120% rocznej zmienności to norma, nie kara jak dla akcji).
- `score_btc_dominance()` — nowa składowa dla altcoinów: siła względem
  30-dniowego zwrotu Bitcoina. Sam BTC-USD dostaje neutralne 50 (punkt
  odniesienia).
- `score_seasonality()` — nowa składowa dla surowców (GLD, USO, UNG, DBA):
  modyfikator na bazie historycznych wzorców sezonowych popytu/podaży.
- Wagi automatycznie renormalizowane do sumy 1.0 dla każdego typu aktywa.

**Darmowe źródła danych live (`external_data.py`, nowy moduł)**
- **Binance** — prawdziwe ceny live (sekundy) dla 8 kryptowalut, bez
  rejestracji. Strona Krypto wyświetla cenę z Binance zamiast Yahoo, gdy
  dostępna (score nadal liczony z Yahoo, dla spójności).
- **CoinGecko** — dominacja BTC/ETH i kapitalizacja całego rynku krypto,
  widoczne jako baner na górze strony Krypto.
- **Alpaca Markets** — opcjonalny live quote (bid/ask) dla akcji USA w
  trybie na żywo na stronie Analizy. Wymaga darmowego klucza API
  (`ALPACA_API_KEY` / `ALPACA_SECRET_KEY`); bez klucza aplikacja działa
  normalnie, korzystając wyłącznie z Yahoo Finance.
- Wszystkie funkcje gracefully degradują do `None` przy błędzie sieci/API —
  Yahoo Finance pozostaje zawsze działającym źródłem zapasowym.
- Status źródeł danych widoczny w Ustawienia → Diagnostyka.

**Sygnały krótkoterminowe (`intraday_signals.py`, nowy moduł)**
- Nowa zakładka „⚡ Sygnały krótkoterminowe” na stronie Analizy.
- **ATR** (Average True Range) — średni dzienny zasięg ruchu, pomocny przy
  ustawianiu stop-lossów.
- **Stochastik %K/%D** — oscylator czulszy na krótkoterminowe odwrócenia
  niż RSI, z wykrywaniem przecięć bullish/bearish.
- **OBV** (On-Balance Volume) — skumulowany wolumen + automatyczne
  wykrywanie dywergencji cena/wolumen.
- **Poziomy wsparcia/oporu** — automatyczne wykrywanie na bazie lokalnych
  ekstremów ceny, narysowane na wykresie.
- Jasne zastrzeżenie w UI: wskaźniki liczone na danych dziennych
  (~15 min opóźnienia Yahoo) — narzędzie dla swing-tradingu, nie
  prawdziwego intraday day-tradingu.

### Zmieniono

- `requirements.txt`: dodano jawną zależność `requests>=2.28,<3.0`
  (wcześniej tylko tranzytywna przez yfinance, teraz używana bezpośrednio
  przez `external_data.py`).
- `.streamlit/secrets.toml.example`: dodano opcjonalny szablon dla
  `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`.
- Sekcja sezonowości i dominacji BTC opisana w dokumentacji (wszystkie 3
  pliki `.docx` zaktualizowane).

### Testy

- 134 → **201 testów** (+67).
- Nowy `tests/test_external_data.py` (20 testów) — Binance/CoinGecko/Alpaca
  z zamockowanym `requests.get`, bez prawdziwych połączeń sieciowych.
- Nowy `tests/test_intraday_signals.py` (25 testów) — ATR, Stochastik, OBV,
  wykrywanie dywergencji, poziomy wsparcia/oporu.
- `tests/test_stock_analyzer.py`: +25 testów dla nowych typów aktywa, wag
  i składowych score krypto/surowców.

---

## [1.0.0] — 2026-06-17

### Pierwsze wydanie publiczne

Wielostronicowa aplikacja Streamlit do analizy technicznej i fundamentalnej
akcji, ETF-ów, kryptowalut i surowców. Score 0–100 oparty o 10 wskaźników
ważonych zależnie od typu aktywa.

**Funkcje:**
- 11 stron: Start, Analiza, Porównanie, Watchlist, Portfolio, Wzrostowe,
  ETF, Krypto, Dziennik, Skaner, Backtest, Ustawienia, O aplikacji.
- Wskaźniki techniczne: RSI, MACD, średnie kroczące, wstęgi Bollingera,
  VWAP, siła relatywna vs indeks, wykrywanie crossover MA50/MA200.
- Scenariusze cenowe: Monte Carlo (GBM), trend liniowy, wygładzanie Holta
  — jasno opisane jako scenariusze, nie prognozy.
- Backtest reguły score z metrykami Sharpe/Sortino/max drawdown,
  walk-forward, heatmapa progów.
- Alerty Telegram i e-mail (próg score, crossover MA).
- Eksport do Excela (Portfolio/Dziennik/Historia score) i PDF (raport
  pojedynczej spółki).
- Tryb na żywo (auto-odświeżanie wykresu przez `st.fragment`).

**Hardening przed launchem:**
- SQLite w trybie WAL + busy_timeout dla współbieżności.
- Szyfrowanie sekretów (Fernet/AES-128-GCM) dla tokenów Telegram i haseł
  SMTP.
- Token bucket + exponential backoff chroniący przed blokadą Yahoo
  Finance (429).
- Rotujące logi plikowe + podgląd w Ustawieniach.
- Graceful degradation przy niedostępności danych (czytelne komunikaty
  zamiast surowych wyjątków).
- Kreator onboardingowy dla nowych użytkowników.
- 134 testy jednostkowe, w pełni offline (syntetyczne dane).

**Disclaimer:** narzędzie edukacyjne i analityczne — nie stanowi porady
inwestycyjnej.
