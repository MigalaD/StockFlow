# Changelog

Wszystkie znaczące zmiany w Analizatorze Spółek są dokumentowane w tym pliku.

Format luźno wzorowany na [Keep a Changelog](https://keepachangelog.com/).
Wersjonowanie: [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

---

## [1.1.0] — 2026-06-25

### Dodano

**Scoring krypto i surowców — pełna separacja typów aktywów**
- Nowy `asset_type="crypto"` osobny od `"commodity"` — inne wagi, inne składowe
- `score_volatility_crypto()` — progi kalibrowane pod zmienność krypto (50–120% rocznie = norma)
- `score_btc_dominance()` — siła altcoina względem 30-dniowego zwrotu BTC
- `score_seasonality()` — modyfikator sezonowy dla GLD/USO/UNG/DBA

**Score krótkoterminowy — `compute_score_krotkoterminowy()`**
- Osobny score swing-tradingowy (0–100) obok istniejącego score długoterminowego
- 7 składowych: RSI-7, Stochastik %K, momentum 5d/10d, wolumen 3d, OBV, VWAP pozycja, Bollinger %B
- Dwa badże w nagłówku Analizy: `📈 Wynik DT` i `⚡ Wynik ST`
- Skaner z przełącznikiem trybu — ranking DT lub ST, heatmapa sektorów per tryb

**Darmowe API live — `external_data.py`**
- **Binance** — ceny i świece OHLCV dla krypto w czasie rzeczywistym (bez rejestracji)
- **CoinGecko** — dominacja BTC/ETH, kapitalizacja rynku krypto
- **Alpaca Markets** — opcjonalny live quote (bid/ask) dla akcji USA
- Graceful degradation — Yahoo Finance zawsze jako fallback

**Wykresy z wyborem interwału**
- Selektor: 1d / 1h / 30m / 15m / 5m / 1m
- Krypto → Binance (prawdziwy live, zero opóźnienia dla każdego interwału)
- Akcje/ETF → Yahoo Finance (~15 min opóźnienia)
- Automatyczny tryb świecowy dla interwałów intraday
- Tryb na żywo z selektorem częstotliwości (15s / 30s / 1min / 2min / 5min)

**Sygnały krótkoterminowe — `intraday_signals.py`**
- Nowa zakładka „⚡ Sygnały krótkoterminowe" w Analizie
- ATR z wyliczonym stop-lossem (1× i 1.5× ATR od ceny)
- Stochastik %K/%D z mini wykresem 60 dni
- OBV z automatycznym wykrywaniem dywergencji
- Poziomy wsparcia/oporu z odległością % od ceny + wykres z etykietami
- Panel syntezy — jeden kolorowy komunikat łączący wszystkie sygnały

**Strona Krypto**
- Baner dominacji BTC/ETH (CoinGecko)
- Ceny live z Binance (score nadal liczony z Yahoo dla spójności)

**Inne**
- `database.py`: migracja nr 2 — kolumna `score_st` w `scan_results`
- `pages/10_Ustawienia.py`: status zewnętrznych źródeł danych
- `LICENSE` i nagłówki copyright (Damian Migała / StockFlow)

### Naprawiono
- `KeyError` na stronie Analizy dla składowych krypto (`volatility_crypto`, `btc_dominance`) — brak wpisów w `OPISY_WSKAZNIKOW`
- `NameError: external_data` w trybie na żywo — brakujący `import` w `common.py`
- `packages.txt` z polskimi komentarzami → błąd apt-get na Streamlit Cloud — plik opróżniony
- Konflikt `libpng16-16` vs `libpng16-16t64` na Debian Trixie
- Poprawa obsługi błędów BTC-USD: trzy warstwy fallback (Binance → Yahoo cached → Yahoo direct)
- `score_banner()` kompatybilny z `score=None`

### Zmieniono
- `requirements.txt`: `requests>=2.28`, Streamlit `>=1.37`
- Nagłówek strony Analizy: dwa score zamiast jednego

### Testy
- 134 → **201 testów** (+67)
- Nowy `tests/test_external_data.py` (20 testów)
- Nowy `tests/test_intraday_signals.py` (25 testów)
- `tests/test_stock_analyzer.py`: +25 testów dla krypto/surowców

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
