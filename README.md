# Analizator Spółek

Wielostronicowy dashboard do analizy technicznej i fundamentalnej spółek,
ETF-ów, kryptowalut i surowców. Narzędzie edukacyjne, **nie porada inwestycyjna**.

Aktualna wersja: **1.1.0** — pełna lista zmian w [CHANGELOG.md](CHANGELOG.md).

## Szybki start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struktura projektu

```
app.py                  ← punkt startowy (streamlit run app.py)
common.py               ← współdzielone helpery, wykresy, cache
external_data.py        ← klienci Binance / CoinGecko / Alpaca (dane live)
intraday_signals.py     ← ATR, Stochastik, OBV, wsparcie/opór (swing-trading)
pages/
  1_📈_Analiza.py       ← analiza jednej spółki (score, wykresy, sygnały krótkoterminowe, PDF, prognozy)
  2_🔀_Porownanie.py    ← porównanie wielu spółek + znormalizowane zwroty
  3_⭐_Watchlist.py     ← obserwowane spółki + alerty
  4_💼_Portfolio.py     ← P&L, alokacja sektorowa, korelacja pozycji
  5_🚀_Wzrostowe.py     ← spółki po niedawnym IPO / wysokiego wzrostu
  6_📦_ETF.py           ← ETF-y i surowce (wagi score dopasowane do typu)
  6b_₿_Krypto.py        ← kryptowaluty (BTC, ETH, SOL, …) + ceny live z Binance
  7_📓_Dziennik.py      ← dziennik decyzji inwestycyjnych
  8_🔍_Skaner.py        ← równoległy skaner rynku (USA/GPW/Europa/Krypto)
  9_🧪_Backtest.py      ← backtest reguły score, walk-forward, heatmapa progów
  10_⚙️_Ustawienia.py  ← Telegram, e-mail, cache, motyw, status źródeł danych
```

### Moduły logiki

| Plik | Opis |
|---|---|
| `stock_analyzer.py` | Score 0–100 (10+ wskaźników), typy aktywa (akcja/ETF/**krypto**/**surowiec** – osobne od v1.1), cache cen |
| `external_data.py` | Darmowe API live: Binance (ceny krypto), CoinGecko (dominacja BTC), Alpaca (akcje USA, opcjonalnie) |
| `intraday_signals.py` | ATR, Stochastik %K/%D, OBV + dywergencja, poziomy wsparcia/oporu (swing-trading) |
| `forecasting.py` | Scenariusze cenowe: Monte Carlo (GBM), trend liniowy, wygładzanie Holta |
| `backtest.py` | Backtest, Sharpe/Sortino, walk-forward, heatmapa progów |
| `portfolio.py` | P&L, alokacja sektorowa, macierz korelacji |
| `scanner.py` | Równoległy skaner (ThreadPoolExecutor, 8 wątków) |
| `rate_limiter.py` | Token bucket + backoff chroniący przed blokadą Yahoo Finance (429) |
| `app_logging.py` | Logowanie do pliku z rotacją (logs/app.log) + podgląd w Ustawieniach |
| `analytics.py` | Agregacje (siła sektorów ze skanu) |
| `excel_export.py` | Eksport Portfolio/Dziennika/Historii do wielozakładkowego .xlsx |
| `database.py` | SQLite: watchlist, portfolio, dziennik, cache cen, score history, alerty; system migracji schematu |
| `strategies.py` | Checklisty stylów inwestowania |
| `pdf_report.py` | Raport PDF (reportlab) |
| `telegram_alerts.py` | Alerty Telegram |
| `email_alerts.py` | Alerty e-mail (SMTP) + digest |
| `scheduler.py` | Cron/Task Scheduler: skan + alerty |
| `tickers.py` | Listy instrumentów (GPW, USA, Europa, ETF, Krypto, Surowce) |

### Wskaźniki i wykresy

- **Wyszukiwarka instrumentów** – w analizie spółki można szukać po nazwie
  (np. „apple”) lub symbolu; podpowiedzi pochodzą z Yahoo Finance.
- **Średnie kroczące** MA 20 / 50 / 200 (krótki, średni i długi horyzont).
- **Wstęgi Bollingera** (MA 20 ± 2σ) – opcjonalna nakładka na wykres;
  pozycja ceny względem wstęg dodatkowo modyfikuje składową „stabilność ceny”.
- **Wykres świecowy (OHLC)** – przełączany obok wykresu liniowego.
- **VWAP** (Volume Weighted Average Price) – opcjonalna nakładka pokazująca
  „sprawiedliwą” cenę ważoną wolumenem; podsumowanie czy cena jest powyżej/poniżej.
- **Tryb na żywo** – wykres analizy odświeża się automatycznie (co 30 s – 5 min,
  do wyboru) bez przeładowania strony, dzięki `st.fragment`. Uwaga: dane Yahoo
  Finance są opóźnione (~15 min), więc nowy punkt pojawia się co kilkanaście minut.
- **Siła relatywna vs indeks** – porównanie rocznego zwrotu spółki z S&P 500
  (lub WIG20 dla GPW): czy radzi sobie lepiej, czy gorzej niż rynek.
- **Alert o przecięciu MA50/MA200** – „złoty krzyż” / „krzyż śmierci”,
  wysyłany na Telegram/e-mail (włączany per spółka w watchliście).
- **Pojedynek 1 vs 1** – porównanie dwóch spółek obok siebie, wskaźnik po wskaźniku.
- **Siła sektorów** – heatmapa średniego wyniku per sektor na podstawie skanu rynku.

### Scoring krypto i surowców (od v1.1)

Kryptowaluty i surowce mają **osobny typ aktywa** (wcześniej traktowane
identycznie) z dedykowanymi składowymi score:

- **Krypto** (`asset_type="crypto"`): `volatility_crypto` zastępuje zwykłą
  zmienność (progi kalibrowane pod realia rynku krypto, gdzie 60-120%
  rocznej zmienności to norma, nie anomalia) + `btc_dominance` – siła
  altcoina względem BTC w ostatnich 30 dniach (BTC sam jest punktem
  odniesienia, dostaje neutralne 50).
- **Surowce** (`asset_type="commodity"` / `etf_commodity`): dochodzi
  `seasonality` – modyfikator na bazie historycznych wzorców sezonowych
  (np. złoto silne Q4/Q1, gaz ziemny silny zimą).

### Sygnały krótkoterminowe (zakładka „⚡” w Analizie, od v1.1)

ATR (zasięg dziennych ruchów, pomocny przy stop-lossach), Stochastik %K/%D
(czulszy na krótkie odwrócenia niż RSI), OBV z wykrywaniem dywergencji
ceny/wolumenu, oraz automatyczne poziomy wsparcia/oporu. **Uwaga:** liczone
na danych dziennych z Yahoo (~15 min opóźnienia) – narzędzie dla
swing-tradingu (dni/tygodnie), nie prawdziwego intraday day-tradingu.

### Źródła danych live (od v1.1)

| Źródło | Co daje | Konfiguracja |
|---|---|---|
| **Binance** | Ceny krypto w czasie rzeczywistym (sekundy) | Brak – publiczne API |
| **CoinGecko** | Dominacja BTC/ETH, kapitalizacja rynku krypto | Brak – publiczne API |
| **Alpaca Markets** | Ceny live (bid/ask) dla akcji/ETF-ów USA | Opcjonalne – darmowy klucz z alpaca.markets |

Yahoo Finance pozostaje głównym źródłem (do liczenia score, dla spójności)
i jedynym źródłem dla GPW oraz rynków europejskich – nie ma dla nich
darmowego API real-time.

## Automatyczne alerty (scheduler)

```bash
# Windows (Harmonogram zadań):
python scheduler.py [usa|gpw|europa|krypto|all]

# Linux/Mac (cron, codziennie 18:00):
0 18 * * * cd /ścieżka/do/apki && python scheduler.py
```

## Testy

```bash
pytest
```

201 testów, działają offline (syntetyczne dane + zamockowane API zamiast
prawdziwych połączeń sieciowych do Yahoo Finance / Binance / CoinGecko / Alpaca).

## Wdrożenie na Streamlit Cloud

1. Wypchnij repo na GitHub (plik `.gitignore` chroni sekrety i bazę).
2. Na share.streamlit.io wskaż `app.py` jako główny plik.
3. W **Settings → Secrets** wklej klucz szyfrowania:
   ```toml
   ENCRYPTION_KEY = "wygenerowany-klucz"
   ```
   Klucz wygenerujesz raz:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. (Opcjonalnie) ogranicz tempo zapytań do Yahoo Finance dla jednego współdzielonego IP:
   ```toml
   YF_RATE_LIMIT = "4"
   ```
5. (Opcjonalnie) darmowy klucz Alpaca Markets dla cen live akcji USA:
   ```toml
   ALPACA_API_KEY = "twój-klucz"
   ALPACA_SECRET_KEY = "twój-sekret"
   ```
   Bez tego aplikacja działa normalnie – po prostu bez dodatkowego źródła
   live dla akcji USA (Binance dla krypto i CoinGecko dla dominacji BTC
   działają zawsze, bez konfiguracji).

**Ważne dla wersji testowej:** Streamlit Cloud kasuje dysk przy każdym
restarcie/redeploy, więc baza (`stock_app.db`) i logi resetują się –
watchlisty, portfolio i ustawienia mogą zniknąć. Dla trwałego przechowywania
podłącz zewnętrzną bazę (np. Postgres/Supabase) w przyszłej wersji.

## Disclaimer

Narzędzie edukacyjne/analityczne. Nie stanowi porady inwestycyjnej.
Dane z Yahoo Finance – mogą być nieaktualne. Decyzje na własną odpowiedzialność.

## Licencja

Copyright (c) 2026 Damian Migała / StockFlow. **Wszystkie prawa zastrzeżone.**
Kopiowanie, używanie, modyfikowanie i dystrybuowanie tego kodu bez pisemnej
zgody właściciela jest zabronione. Pełne warunki w pliku [LICENSE](LICENSE).
