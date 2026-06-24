# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Stock Analytics Tool
=====================
Narzędzie analityczne (NIE porada inwestycyjna) do oceny spółek na podstawie
sygnałów technicznych i fundamentalnych. Generuje "score" 0-100 z rozbiciem
na poszczególne wskaźniki.

Instalacja:
    pip install yfinance pandas numpy

Użycie:
    python stock_analyzer.py AAPL MSFT TSLA
"""

from __future__ import annotations

import sys
import time
import functools
import numpy as np
import pandas as pd
import yfinance as yf

import database as db
from rate_limiter import rate_limited, with_backoff
import external_data


# ----------------------------------------------------------------------
# WALIDACJA / NORMALIZACJA SYMBOLU
# Czyści wejście od użytkownika ("aapl ", " CDR.WA") do kanonicznej formy.
# ----------------------------------------------------------------------
def sanitize_ticker(ticker: str) -> str:
    """Normalizuje symbol: usuwa białe znaki i zamienia na wielkie litery.

    Zwraca pusty string dla wejścia, które nie może być prawidłowym symbolem
    (None, same spacje). Nie waliduje istnienia spółki - to robi dopiero
    zapytanie do Yahoo Finance.
    """
    if not ticker:
        return ""
    cleaned = ticker.strip().upper()
    # Yahoo używa myślnika dla klas akcji (BRK-B) i sufiksu giełdy (.WA),
    # więc dozwolone znaki to litery, cyfry, kropka, myślnik i daszek (^GSPC).
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^=")
    if not cleaned or any(ch not in allowed for ch in cleaned):
        # odfiltruj oczywiste śmieci, ale zostaw symbol jeśli wygląda sensownie
        cleaned = "".join(ch for ch in cleaned if ch in allowed)
    return cleaned


# ----------------------------------------------------------------------
# RETRY + RATE LIMITING - Yahoo Finance agresywnie ogranicza ruch (HTTP 429).
# `with_backoff` ponawia z wykładniczym opóźnieniem (dłuższym przy 429),
# a `rate_limited` przepuszcza realne zapytania sieciowe przez globalny
# token bucket (patrz rate_limiter.py), żeby nie przekroczyć ~8 req/s nawet
# przy równoległym skanowaniu.
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# CACHE CEN - lokalna baza SQLite współdzielona między userami/sesjami.
# Zmniejsza liczbę zapytań do Yahoo Finance (szybsze ładowanie, mniejsze
# ryzyko rate-limitu). Domyślny czas życia: 15 minut (900s).
# ----------------------------------------------------------------------
PRICE_CACHE_TTL = 900


def _df_to_cache_json(df: pd.DataFrame) -> str:
    out = df.copy()
    out.index = out.index.astype(str)
    return out.to_json(orient="split", date_format="iso")


def _df_from_cache_json(data_json: str) -> pd.DataFrame:
    import io
    df = pd.read_json(io.StringIO(data_json), orient="split")
    df.index = pd.to_datetime(df.index)
    return df


@with_backoff(times=3, base_delay=1.0)
def fetch_history(stock: "yf.Ticker", period: str, interval: str = "1d") -> pd.DataFrame:
    ticker = getattr(stock, "ticker", None)

    if ticker and interval == "1d":
        try:
            cached = db.get_price_cache(ticker, period, max_age_seconds=PRICE_CACHE_TTL)
            if cached:
                return _df_from_cache_json(cached)
        except Exception:
            pass

    # Realne zapytanie sieciowe - przepuszczone przez globalny rate limiter.
    df = _fetch_history_network(stock, period, interval)

    if ticker and interval == "1d" and not df.empty:
        try:
            db.set_price_cache(ticker, period, _df_to_cache_json(df))
        except Exception:
            pass

    return df


@rate_limited
def _fetch_history_network(stock: "yf.Ticker", period: str, interval: str) -> pd.DataFrame:
    return stock.history(period=period, interval=interval)


@with_backoff(times=2, base_delay=1.0)
@rate_limited
def fetch_info(stock: "yf.Ticker") -> dict:
    try:
        return stock.info or {}
    except Exception:
        return {}


def search_tickers(query: str, limit: int = 8) -> list[dict]:
    """Wyszukuje instrumenty po nazwie lub symbolu przez Yahoo Finance.

    Pozwala użytkownikowi wpisać np. "apple" zamiast pamiętać symbol "AAPL".
    Zwraca listę słowników: {symbol, name, exchange, type}. Przy błędzie
    sieci lub braku wyników zwraca pustą listę (nie rzuca wyjątku).
    """
    query = (query or "").strip()
    if not query:
        return []

    try:
        search = _search_network(query, limit)
        quotes = search.quotes or []
    except Exception:
        return []

    results = []
    for q in quotes:
        symbol = q.get("symbol")
        if not symbol:
            continue
        results.append({
            "symbol": symbol,
            "name": q.get("longname") or q.get("shortname") or symbol,
            "exchange": q.get("exchange", ""),
            "type": (q.get("quoteType") or "").upper(),
        })
    return results


@rate_limited
def _search_network(query: str, limit: int):
    return yf.Search(query, max_results=limit)


def validate_ticker(ticker: str) -> dict:
    """Sprawdza, czy symbol ma sensowne, świeże dane w Yahoo Finance.

    yfinance czasem "cicho" zwraca pustkę dla delistowanej spółki albo
    literówki w symbolu. Ta funkcja sprawdza, czy są jakiekolwiek dane
    z ostatnich ~7 dni, zanim dodamy pozycję do watchlisty/portfolio.

    Zwraca dict: {valid: bool, ticker: str, reason: str, name: str, price: float|None}.
    """
    ticker = sanitize_ticker(ticker)
    if not ticker:
        return {"valid": False, "ticker": ticker,
                "reason": "Pusty lub nieprawidłowy symbol.", "name": None, "price": None}

    try:
        stock = yf.Ticker(ticker)
        df = fetch_history(stock, period="7d")
    except Exception as e:
        return {"valid": False, "ticker": ticker,
                "reason": f"Błąd pobierania danych: {e}", "name": None, "price": None}

    if df is None or df.empty:
        return {"valid": False, "ticker": ticker,
                "reason": "Brak danych - możliwa literówka lub delisting.",
                "name": None, "price": None}

    df = df.dropna(subset=["Close"])
    if df.empty:
        return {"valid": False, "ticker": ticker,
                "reason": "Brak prawidłowych cen w ostatnich dniach.",
                "name": None, "price": None}

    try:
        info = fetch_info(stock)
    except Exception:
        info = {}
    name = info.get("longName") or info.get("shortName") or ticker

    return {
        "valid": True,
        "ticker": ticker,
        "reason": "OK",
        "name": name,
        "price": round(float(df["Close"].iloc[-1]), 2),
    }


# ----------------------------------------------------------------------
# BENCHMARKI SEKTOROWE (orientacyjne, do porównania P/E spółki z "typowym"
# poziomem dla branży). To zgrubne wartości - edytuj swobodnie, jeśli masz
# lepsze dane dla swojego rynku.
# ----------------------------------------------------------------------
SECTOR_PE_BENCHMARKS = {
    "Technology": 30,
    "Communication Services": 22,
    "Consumer Cyclical": 25,
    "Consumer Defensive": 22,
    "Healthcare": 25,
    "Financial Services": 13,
    "Energy": 11,
    "Industrials": 20,
    "Basic Materials": 14,
    "Real Estate": 18,
    "Utilities": 18,
}


def compare_to_sector_pe(pe: float | None, sector: str | None) -> str | None:
    """Zwraca krótki opis porównania P/E spółki do orientacyjnej normy sektora."""
    if pe is None or not sector or sector not in SECTOR_PE_BENCHMARKS:
        return None
    benchmark = SECTOR_PE_BENCHMARKS[sector]
    diff_pct = (pe / benchmark - 1) * 100
    if diff_pct > 25:
        return f"P/E {pe:.1f} jest wyraźnie WYŻSZE niż typowe dla sektora '{sector}' (~{benchmark})"
    if diff_pct < -25:
        return f"P/E {pe:.1f} jest wyraźnie NIŻSZE niż typowe dla sektora '{sector}' (~{benchmark})"
    return f"P/E {pe:.1f} jest zbliżone do typowego dla sektora '{sector}' (~{benchmark})"


# ----------------------------------------------------------------------
# BETA / KORELACJA Z INDEKSEM (informacyjne - nie wchodzi do score)
# ----------------------------------------------------------------------
def _index_for_ticker(ticker: str) -> str:
    return "^WIG20" if ticker.upper().endswith(".WA") else "^GSPC"


@with_backoff(times=2, base_delay=1.0)
def compute_beta(ticker: str, stock_df: pd.DataFrame, period: str = "1y") -> dict | None:
    """
    Liczy beta i korelację dziennych zwrotów spółki względem indeksu
    (S&P 500 dla rynku USA, WIG20 dla GPW). Wartości informacyjne -
    pomagają ocenić, jak "nerwowo" spółka reaguje na ruchy całego rynku.

    beta > 1  -> spółka zwykle rusza się BARDZIEJ niż rynek
    beta < 1  -> spółka zwykle rusza się MNIEJ niż rynek
    beta ~ 1  -> podobnie jak rynek
    """
    index_ticker = _index_for_ticker(ticker)
    try:
        index_df = fetch_history(yf.Ticker(index_ticker), period=period)
    except Exception:
        return None
    if index_df.empty:
        return None

    stock_ret = stock_df["Close"].pct_change().dropna()
    index_ret = index_df["Close"].pct_change().dropna()

    joined = pd.concat([stock_ret, index_ret], axis=1, join="inner")
    joined.columns = ["stock", "index"]
    joined = joined.dropna()

    if len(joined) < 30:
        return None

    covariance = joined["stock"].cov(joined["index"])
    variance = joined["index"].var()
    if variance == 0:
        return None

    beta = covariance / variance
    correlation = joined["stock"].corr(joined["index"])

    return {
        "beta": round(float(beta), 2),
        "correlation": round(float(correlation), 2),
        "index": index_ticker,
    }


def compute_relative_strength(
    ticker: str,
    stock_df: pd.DataFrame,
    period: str = "1y",
) -> dict | None:
    """Porównuje zwrot spółki ze zwrotem jej indeksu odniesienia w danym okresie.

    "Relative strength" (siła relatywna) odpowiada na pytanie: czy spółka
    poradziła sobie LEPIEJ czy GORZEJ niż szeroki rynek? To jedno z
    najpraktyczniejszych porównań - spółka może rosnąć, ale jeśli rynek rósł
    szybciej, to relatywnie jest słaba (i odwrotnie).

    Zwraca dict z procentowym zwrotem spółki, indeksu i ich różnicą
    (outperformance), albo None gdy brakuje danych.
    """
    index_ticker = _index_for_ticker(ticker)
    try:
        index_df = fetch_history(yf.Ticker(index_ticker), period=period)
    except Exception:
        return None
    if index_df is None or index_df.empty or stock_df.empty:
        return None

    stock_close = stock_df["Close"].dropna()
    index_close = index_df["Close"].dropna()
    if len(stock_close) < 2 or len(index_close) < 2:
        return None

    # Dopasuj okno czasowe do wspólnych dat, żeby porównanie było uczciwe.
    joined = pd.concat([stock_close, index_close], axis=1, join="inner").dropna()
    if len(joined) < 2:
        return None
    joined.columns = ["stock", "index"]

    stock_return = (joined["stock"].iloc[-1] / joined["stock"].iloc[0] - 1) * 100
    index_return = (joined["index"].iloc[-1] / joined["index"].iloc[0] - 1) * 100
    outperformance = stock_return - index_return

    return {
        "index": index_ticker,
        "stock_return_pct": round(float(stock_return), 1),
        "index_return_pct": round(float(index_return), 1),
        "outperformance_pct": round(float(outperformance), 1),
        "period": period,
    }


def detect_ma_crossover(df: pd.DataFrame) -> dict | None:
    """Wykrywa przecięcie średnich MA50 i MA200 ("złoty krzyż" / "krzyż śmierci").

    Zwraca:
    - state: aktualny stan ('golden' gdy MA50 > MA200, 'death' gdy poniżej)
    - crossed: czy przecięcie nastąpiło DZIŚ (zmiana względem poprzedniego dnia)
    - type: 'golden' / 'death' jeśli crossed, inaczej None

    "Złoty krzyż" (MA50 przecina MA200 od dołu) to klasyczny sygnał byczy,
    "krzyż śmierci" (MA50 spada poniżej MA200) - niedźwiedzi. Wymaga kolumn
    MA50 i MA200 w df. Zwraca None gdy brak wystarczających danych.
    """
    if "MA50" not in df.columns or "MA200" not in df.columns:
        return None

    valid = df.dropna(subset=["MA50", "MA200"])
    if len(valid) < 2:
        return None

    ma50_now,  ma200_now  = valid["MA50"].iloc[-1], valid["MA200"].iloc[-1]
    ma50_prev, ma200_prev = valid["MA50"].iloc[-2], valid["MA200"].iloc[-2]

    state_now  = "golden" if ma50_now  > ma200_now  else "death"
    state_prev = "golden" if ma50_prev > ma200_prev else "death"

    crossed = state_now != state_prev
    return {
        "state": state_now,
        "crossed": crossed,
        "type": state_now if crossed else None,
    }


# ----------------------------------------------------------------------
# KONFIGURACJA WAG - edytuj te wartości, żeby zmienić ważność sygnałów
# ----------------------------------------------------------------------
WEIGHTS = {
    "rsi": 0.11,
    "trend_ma": 0.15,       # cena vs średnie ruchome (50/200)
    "macd": 0.11,
    "volume": 0.07,
    "volatility": 0.07,
    "valuation": 0.11,      # P/E vs branża/historia
    "momentum": 0.11,       # zmiana ceny w ostatnich okresach
    "dividend": 0.09,       # dywidenda i jej bezpieczeństwo
    "sentiment": 0.08,      # sentiment z ostatnich newsów
    "fundamentals": 0.10,   # wzrost przychodów, ROE, dług, cash flow
}

# ----------------------------------------------------------------------
# TYPY AKTYW - ETF-y i surowce nie mają fundamentów spółek (P/E, dywidenda,
# dług, wzrost przychodów), więc te składowe są dla nich wykluczane, a
# pozostałe wagi przeliczane proporcjonalnie tak, by sumowały się do 1.0.
# ----------------------------------------------------------------------

# Składowe wykluczone dla danego typu aktywa (None/brak danych i tak by
# dały neutralne 50, ale wtedy ich waga "rozmywałaby" wynik w kierunku
# środka - lepiej przeliczyć wagi na te wskaźniki, które faktycznie mają
# sens dla danego typu instrumentu).
EXCLUDED_COMPONENTS_BY_ASSET_TYPE = {
    "stock": set(),
    "etf": {"fundamentals"},
    "etf_commodity": {"valuation", "dividend", "fundamentals"},
    "commodity": {"valuation", "dividend", "fundamentals"},
    "crypto": {"valuation", "dividend", "fundamentals"},
    "other": {"valuation", "dividend", "fundamentals"},
}

# Krypto i surowce mają wykluczone te same fundamentalne składowe co wyżej,
# ale dodatkowo dostają WŁASNE składowe (volatility_crypto / btc_dominance
# dla krypto; seasonality dla surowców) ZAMIAST zwykłej "volatility".
# Patrz get_weights_for_asset_type() - tam dzieje się podmiana.
CRYPTO_EXTRA_COMPONENTS = {"btc_dominance"}
COMMODITY_EXTRA_COMPONENTS = {"seasonality"}

ASSET_TYPE_LABELS = {
    "stock": "Akcja",
    "etf": "ETF",
    "etf_commodity": "ETF (towarowy)",
    "commodity": "Surowiec / kontrakt",
    "crypto": "Kryptowaluta",
    "other": "Inny instrument",
}


def get_asset_type(info: dict, ticker: str | None = None) -> str:
    """
    Klasyfikuje instrument na podstawie pola `quoteType` z yfinance:
    EQUITY -> akcja, ETF -> etf, CRYPTOCURRENCY -> crypto,
    FUTURE/CURRENCY/COMMODITY -> surowiec (commodity).

    Krypto i surowce były wcześniej traktowane identycznie ("commodity"),
    ale mają zupełnie inną charakterystykę: krypto ma wielokrotnie wyższą
    "normalną" zmienność (60-150% rocznie to nic niezwykłego, podczas gdy
    dla akcji to już ekstremum) i brak fundamentów makro typu sezonowość.
    Dlatego od teraz rozróżniamy je jako osobne typy aktywów z osobnymi
    wagami i osobnymi składowymi score (patrz get_weights_for_asset_type).

    Specjalny przypadek: ETF-y towarowe (np. GLD, SLV, USO) mają
    quoteType=ETF, ale - tak jak surowce - nie mają P/E ani dywidendy.
    Jeśli ETF nie ma żadnej z tych wartości, traktujemy go jak
    'etf_commodity' (wyklucza też wycenę/dywidendę z score).

    Parametr `ticker` (opcjonalny) to dodatkowe zabezpieczenie: jeśli Yahoo
    nie poda quoteType="CRYPTOCURRENCY" (zdarza się dla niektórych mniej
    popularnych monet), a symbol kończy się na "-USD" (konwencja Yahoo dla
    krypto), i tak rozpoznajemy to jako krypto.
    """
    quote_type = (info.get("quoteType") or "").upper()
    if quote_type == "EQUITY":
        return "stock"
    if quote_type == "ETF":
        if info.get("trailingPE") is None and info.get("dividendYield") is None:
            return "etf_commodity"
        return "etf"
    if quote_type == "CRYPTOCURRENCY":
        return "crypto"
    if quote_type in ("FUTURE", "CURRENCY", "COMMODITY"):
        return "commodity"
    if quote_type == "":
        # Brak informacji od Yahoo - sprawdź ticker jako fallback zanim
        # domyślnie potraktujemy jak akcję (konwencja: krypto = "XXX-USD").
        if ticker and ticker.upper().endswith("-USD"):
            return "crypto"
        return "stock"
    return "other"


def get_weights_for_asset_type(asset_type: str) -> dict:
    """
    Zwraca wagi przeliczone dla danego typu aktywa - wyklucza nieadekwatne
    składowe i renormalizuje pozostałe tak, by sumowały się do 1.0.

    Dla krypto: zwykła 'volatility' jest ZASTĘPOWANA przez 'volatility_crypto'
    (te same wagi, ale inna funkcja licząca - kalibrowana pod zmienność
    krypto) i dochodzi nowa składowa 'btc_dominance' (waga 0.08, kosztem
    pozostałych, renormalizowana).

    Dla surowców: dochodzi 'seasonality' (waga 0.08) na podobnej zasadzie.
    """
    excluded = EXCLUDED_COMPONENTS_BY_ASSET_TYPE.get(asset_type, set())
    remaining = {k: v for k, v in WEIGHTS.items() if k not in excluded}

    if asset_type == "crypto":
        # Podmień 'volatility' na 'volatility_crypto' z tą samą wagą bazową.
        if "volatility" in remaining:
            remaining["volatility_crypto"] = remaining.pop("volatility")
        # Dodaj dominację BTC jako nową składową (waga stała 0.08 przed
        # renormalizacją - dla samego BTC ta składowa i tak da neutralne 50,
        # patrz score_btc_dominance).
        remaining["btc_dominance"] = 0.08

    elif asset_type in ("commodity", "etf_commodity"):
        remaining["seasonality"] = 0.08

    total = sum(remaining.values())
    if total <= 0:
        return dict(WEIGHTS)
    return {k: v / total for k, v in remaining.items()}


PERIOD = "1y"        # historia danych
INTERVAL = "1d"

# Krótkie nazwy wskaźników (PL) - używane przez dashboard i raporty PDF
INDICATOR_NAMES = {
    "rsi": "Siła trendu (RSI)",
    "trend_ma": "Kierunek trendu",
    "macd": "Zmiana momentum (MACD)",
    "volume": "Zainteresowanie inwestorów (wolumen)",
    "volatility": "Stabilność ceny",
    "valuation": "Wycena (P/E)",
    "momentum": "Ostatnie zmiany ceny",
    "dividend": "Dywidenda",
    "sentiment": "Sentyment newsów",
    "fundamentals": "Fundamenty (wzrost, ROE, dług, cash flow)",
}


# ----------------------------------------------------------------------
# WSKAŹNIKI TECHNICZNE
# ----------------------------------------------------------------------
def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Oblicza wstęgi Bollingera wokół średniej kroczącej z `window` dni.

    Wstęga środkowa to prosta średnia krocząca (domyślnie 20-dniowa - to
    standard dla Bollingera). Wstęgi górna i dolna leżą `num_std` odchyleń
    standardowych od środka i pokazują "typowy" zakres wahań ceny: gdy cena
    dotyka górnej wstęgi, bywa uznawana za chwilowo przegrzaną, a przy dolnej
    - za wyprzedaną.

    Zwraca krotkę (środek, górna, dolna) jako serie pandas.
    """
    middle = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    upper = middle + num_std * rolling_std
    lower = middle - num_std * rolling_std
    return middle, upper, lower


# ----------------------------------------------------------------------
# SKŁADOWE SCORE (każda zwraca wartość 0-100, gdzie 100 = najbardziej "bullish")
# ----------------------------------------------------------------------
def score_rsi(df: pd.DataFrame) -> tuple[float, str]:
    val = df["RSI"].dropna()
    if val.empty:
        return 50, "brak danych RSI"
    val = float(val.iloc[-1])
    # RSI < 30 = wyprzedanie (potencjalnie pozytywne), > 70 = przegrzanie
    if val <= 30:
        return 80, f"RSI={val:.1f} (wyprzedanie)"
    if val >= 70:
        return 20, f"RSI={val:.1f} (przegrzanie)"
    # liniowo między 30-70, środek (50) = neutralny score 50
    return float(100 - val), f"RSI={val:.1f} (neutralnie)"


def score_trend_ma(df: pd.DataFrame) -> tuple[float, str]:
    price = df["Close"].iloc[-1]
    ma50 = df["MA50"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]
    if np.isnan(ma200):
        return 50, "brak danych do MA200"

    score = 50
    notes = []
    if price > ma50:
        score += 15
        notes.append("cena > MA50")
    else:
        score -= 15
        notes.append("cena < MA50")

    if price > ma200:
        score += 15
        notes.append("cena > MA200")
    else:
        score -= 15
        notes.append("cena < MA200")

    if ma50 > ma200:
        score += 10
        notes.append("złoty krzyż (MA50>MA200)")
    else:
        score -= 10
        notes.append("krzyż śmierci (MA50<MA200)")

    return float(np.clip(score, 0, 100)), ", ".join(notes)


def score_macd(df: pd.DataFrame) -> tuple[float, str]:
    macd_val = df["MACD"].iloc[-1]
    signal_val = df["MACD_signal"].iloc[-1]

    if np.isnan(macd_val) or np.isnan(signal_val):
        return 50, "brak danych MACD"

    macd_prev = df["MACD"].iloc[-2]
    signal_prev = df["MACD_signal"].iloc[-2]

    crossed_up   = (not np.isnan(macd_prev)) and macd_prev < signal_prev and macd_val > signal_val
    crossed_down = (not np.isnan(macd_prev)) and macd_prev > signal_prev and macd_val < signal_val

    if crossed_up:
        return 85, "MACD przeciął sygnał w góre (bullish crossover)"
    if crossed_down:
        return 15, "MACD przeciął sygnał w dół (bearish crossover)"
    if macd_val > signal_val:
        return 65, "MACD > sygnał (trend wzrostowy)"
    return 35, "MACD < sygnał (trend spadkowy)"


def score_volume(df: pd.DataFrame) -> tuple[float, str]:
    vol = df["Volume"]
    avg_vol = vol.rolling(20).mean().iloc[-1]
    last_vol = vol.iloc[-1]
    if np.isnan(avg_vol) or avg_vol == 0:
        return 50, "brak danych"

    ratio = last_vol / avg_vol
    price_change = df["Close"].pct_change().iloc[-1]

    if ratio > 1.5 and price_change > 0:
        return 75, f"wysoki wolumen ({ratio:.1f}x) + wzrost ceny"
    if ratio > 1.5 and price_change < 0:
        return 25, f"wysoki wolumen ({ratio:.1f}x) + spadek ceny"
    return 50, f"wolumen normalny ({ratio:.1f}x średniej)"


def compute_vwap(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Liczy kroczący VWAP (Volume Weighted Average Price) z `window` dni.

    VWAP to średnia cena ważona wolumenem - pokazuje "sprawiedliwą" cenę,
    przy której faktycznie handlowano. Cena powyżej VWAP sugeruje, że
    kupujący są skłonni płacić więcej niż średnia ważona obrotem (siła
    popytu); poniżej - odwrotnie. To jeden z najczęściej używanych
    wskaźników przez inwestorów instytucjonalnych.

    Używa ceny typowej (high+low+close)/3, jeśli dostępne kolumny OHLC;
    w przeciwnym razie samej ceny zamknięcia. Zwraca serię pandas.
    """
    if "Volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)

    if {"High", "Low"}.issubset(df.columns):
        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    else:
        typical_price = df["Close"]

    volume = df["Volume"].replace(0, np.nan)
    pv = typical_price * volume
    vwap = (
        pv.rolling(window).sum()
        / volume.rolling(window).sum()
    )
    return vwap


def vwap_position(df: pd.DataFrame, window: int = 20) -> dict | None:
    """Zwraca położenie aktualnej ceny względem VWAP.

    {vwap: float, price: float, above: bool, distance_pct: float} albo None.
    """
    vwap = compute_vwap(df, window=window)
    vwap = vwap.dropna()
    if vwap.empty:
        return None
    last_vwap = float(vwap.iloc[-1])
    last_price = float(df["Close"].iloc[-1])
    if last_vwap == 0:
        return None
    return {
        "vwap": round(last_vwap, 2),
        "price": round(last_price, 2),
        "above": last_price > last_vwap,
        "distance_pct": round((last_price / last_vwap - 1) * 100, 2),
    }


def score_volatility(df: pd.DataFrame) -> tuple[float, str]:
    """Ocenia stabilność ceny na podstawie zannualizowanej zmienności,
    uzupełnioną o położenie ceny względem wstęg Bollingera (jeśli dostępne).

    Sama zmienność daje bazowy wynik (niska = stabilniej). Położenie przy
    dolnej wstędze Bollingera lekko podnosi wynik (cena nisko w swoim
    typowym zakresie), a przy górnej - lekko obniża (cena wysoko).
    """
    returns = df["Close"].pct_change()
    vol_30d = returns.rolling(30).std().iloc[-1] * np.sqrt(252)  # zannualizowana
    if np.isnan(vol_30d):
        return 50, "brak danych"

    vol_pct = vol_30d * 100
    if vol_pct < 20:
        score, note = 65, f"niska zmienność ({vol_pct:.1f}% rocznie)"
    elif vol_pct > 60:
        score, note = 30, f"bardzo wysoka zmienność ({vol_pct:.1f}% rocznie)"
    else:
        score, note = 50, f"umiarkowana zmienność ({vol_pct:.1f}% rocznie)"

    # Kontekst Bollingera: gdzie cena leży w swoim "typowym" zakresie.
    pct_b = _bollinger_percent_b(df)
    if pct_b is not None:
        if pct_b <= 0.0:
            score += 10
            note += "; cena poniżej dolnej wstęgi Bollingera (wyprzedanie)"
        elif pct_b >= 1.0:
            score -= 10
            note += "; cena powyżej górnej wstęgi Bollingera (przegrzanie)"
        elif pct_b < 0.2:
            score += 5
            note += "; cena przy dolnej wstędze Bollingera"
        elif pct_b > 0.8:
            score -= 5
            note += "; cena przy górnej wstędze Bollingera"

    return float(np.clip(score, 0, 100)), note


def _bollinger_percent_b(df: pd.DataFrame) -> float | None:
    """Zwraca %B: położenie ceny względem wstęg Bollingera.

    0.0 = na dolnej wstędze, 1.0 = na górnej, 0.5 = na środkowej.
    Wartości <0 lub >1 oznaczają wyjście ceny poza wstęgi. Zwraca None,
    jeśli wstęgi nie zostały policzone (np. za mało danych).
    """
    if "BB_upper" not in df.columns or "BB_lower" not in df.columns:
        return None
    upper = df["BB_upper"].iloc[-1]
    lower = df["BB_lower"].iloc[-1]
    price = df["Close"].iloc[-1]
    if np.isnan(upper) or np.isnan(lower) or upper == lower:
        return None
    return float((price - lower) / (upper - lower))


# ----------------------------------------------------------------------
# SCORING DEDYKOWANY DLA KRYPTO
# Krypto ma WIELOKROTNIE wyższą "normalną" zmienność niż akcje (60-150%
# rocznie to norma, nie anomalia). Stosowanie progów score_volatility()
# (kalibrowanych pod akcje, gdzie >60% to "bardzo wysoka zmienność") do
# Bitcoina strukturalnie zaniża jego wynik tylko dlatego, że jest krypto -
# nie dlatego, że dzieje się coś niezwykłego. Dlatego osobna funkcja
# z progami skalowanymi pod realia rynku krypto.
# ----------------------------------------------------------------------
def score_volatility_crypto(df: pd.DataFrame) -> tuple[float, str]:
    """Ocenia stabilność ceny krypto - progi zmienności kalibrowane pod
    realia rynku kryptowalut, nie pod akcje.

    Orientacyjne poziomy roczne (na podstawie historii BTC/ETH/altcoinów):
    < 50%  - niska jak na krypto (zwykle tylko duże, dojrzałe coiny w
             spokojnym okresie rynku)
    50-120% - normalna zmienność krypto (większość czasu dla BTC/ETH)
    > 120%  - podwyższona, typowa dla mniejszych altcoinów lub okresów
              dużej niepewności rynkowej
    > 250%  - ekstremalna, nawet jak na krypto
    """
    returns = df["Close"].pct_change()
    vol_30d = returns.rolling(30).std().iloc[-1] * np.sqrt(252)
    if np.isnan(vol_30d):
        return 50, "brak danych"

    vol_pct = vol_30d * 100
    if vol_pct < 50:
        score, note = 65, f"niska zmienność jak na krypto ({vol_pct:.0f}% rocznie)"
    elif vol_pct < 120:
        score, note = 55, f"normalna zmienność krypto ({vol_pct:.0f}% rocznie)"
    elif vol_pct < 250:
        score, note = 35, f"podwyższona zmienność ({vol_pct:.0f}% rocznie)"
    else:
        score, note = 20, f"ekstremalna zmienność, nawet jak na krypto ({vol_pct:.0f}% rocznie)"

    # Kontekst Bollingera - tak samo jak w score_volatility (akcje).
    pct_b = _bollinger_percent_b(df)
    if pct_b is not None:
        if pct_b <= 0.0:
            score += 10
            note += "; cena poniżej dolnej wstęgi Bollingera (wyprzedanie)"
        elif pct_b >= 1.0:
            score -= 10
            note += "; cena powyżej górnej wstęgi Bollingera (przegrzanie)"
        elif pct_b < 0.2:
            score += 5
            note += "; cena przy dolnej wstędze Bollingera"
        elif pct_b > 0.8:
            score -= 5
            note += "; cena przy górnej wstędze Bollingera"

    return float(np.clip(score, 0, 100)), note


def score_btc_dominance(ticker: str, df: pd.DataFrame) -> tuple[float, str]:
    """Dla altcoinów: ocenia siłę względem Bitcoina (czy bije BTC, czy
    zostaje w tyle) - analogicznie do relative strength vs S&P 500 dla akcji.

    Dla samego BTC-USD zwraca neutralne 50 (Bitcoin jest punktem
    odniesienia, nie ma sensu porównywać go z samym sobą).

    Logika: pobiera 30-dniowy zwrot danego altcoina i 30-dniowy zwrot BTC
    (z lokalnie dostępnych danych - nie wymaga dodatkowego zapytania
    sieciowego), porównuje je. Altcoin bijący BTC dostaje wyższy wynik -
    sugeruje to "wiarę rynku" w dany projekt ponad ogólny sentyment krypto.
    Dodatkowo, jeśli dostępna jest aktualna dominacja BTC (CoinGecko),
    dolicza się to jako kontekst w opisie (nie wpływa na liczbę punktów -
    to dane rynkowe ogólne, nie specyficzne dla danego altcoina).
    """
    if ticker.upper() == "BTC-USD":
        dom = external_data.get_btc_dominance()
        if dom:
            return 50, f"BTC jest punktem odniesienia (dominacja rynku: {dom['btc_dominance_pct']:.1f}%)"
        return 50, "BTC jest punktem odniesienia"

    close = df["Close"]
    if len(close) < 31:
        return 50, "brak wystarczających danych"

    altcoin_ret_30d = (close.iloc[-1] / close.iloc[-31] - 1) * 100

    btc_ret_30d = None
    try:
        btc_stock = yf.Ticker("BTC-USD")
        btc_df = fetch_history(btc_stock, period="3mo", interval="1d")
        if not btc_df.empty and len(btc_df) >= 31:
            btc_close = btc_df["Close"].dropna()
            if len(btc_close) >= 31:
                btc_ret_30d = (btc_close.iloc[-1] / btc_close.iloc[-31] - 1) * 100
    except Exception:
        btc_ret_30d = None

    if btc_ret_30d is None:
        return 50, "brak danych BTC do porównania"

    outperformance = altcoin_ret_30d - btc_ret_30d
    # +/-30 pkt różnicy w zwrocie mapuje na +/-25 punktów score wokół 50
    score = 50 + np.clip(outperformance, -30, 30) / 30 * 25
    score = float(np.clip(score, 0, 100))

    kierunek = "bije BTC" if outperformance > 0 else "słabszy niż BTC"
    note = (
        f"30d: ten coin {altcoin_ret_30d:+.1f}% vs BTC {btc_ret_30d:+.1f}% "
        f"({kierunek} o {abs(outperformance):.1f} pkt proc.)"
    )
    return score, note


# ----------------------------------------------------------------------
# SCORING DEDYKOWANY DLA SUROWCÓW
# Surowce mają silne wzorce sezonowe wynikające z fizycznego popytu/podaży
# (zima -> popyt na gaz, lato -> sezon zbiorów w rolnictwie, itd.). To
# dodatkowy kontekst, którego nie mają akcje - prosta tabela miesięcznych
# modyfikatorów na bazie ogólnie znanych wzorców sezonowych.
# ----------------------------------------------------------------------

# Modyfikator sezonowy per miesiąc (1=styczeń...12=grudzień) dla każdego
# tickera surowcowego. Wartości to ORIENTACYJNE, historyczne tendencje
# (nie gwarancje) - oparte na fizycznych cyklach popytu/podaży:
#   GLD (złoto): sezonowo silniejsze Q4/Q1 (popyt jubilerski - indyjski
#                sezon ślubny, chiński Nowy Rok, zachodnie święta)
#   USO (ropa WTI): sezon jazdy letniej w USA podbija popyt wiosną/latem
#   UNG (gaz ziemny): silny popyt grzewczy zimą
#   DBA (rolnictwo): zmienne w zależności od cyklu zbiorów - uproszczone
_SEASONALITY_BY_TICKER = {
    "GLD":  {1: 5, 2: 3, 3: 0, 4: 0, 5: 0, 6: -3, 7: -3, 8: 0, 9: 2, 10: 5, 11: 5, 12: 3},
    "USO":  {1: -3, 2: 0, 3: 3, 4: 5, 5: 5, 6: 3, 7: 0, 8: 0, 9: -3, 10: -5, 11: -3, 12: -2},
    "UNG":  {1: 5, 2: 5, 3: 0, 4: -3, 5: -5, 6: -3, 7: -2, 8: -2, 9: 0, 10: 3, 11: 5, 12: 5},
    "DBA":  {1: 0, 2: 0, 3: 2, 4: 2, 5: 0, 6: -2, 7: -2, 8: 0, 9: 2, 10: 2, 11: 0, 12: 0},
}


def score_seasonality(ticker: str) -> tuple[float, str]:
    """Modyfikator sezonowy dla surowców na bazie znanych, historycznych
    wzorców popytowo-podażowych. Zwraca score wokół 50 (neutralnie), +/-5
    punktów w zależności od miesiąca i tickera.

    UWAGA: to orientacyjne, historyczne tendencje - nie reguła ani
    gwarancja. Pojedynczy rok może łatwo odbiegać od wzorca (pogoda,
    geopolityka, decyzje OPEC itd. dominują nad sezonowością).
    """
    import datetime as _dt

    table = _SEASONALITY_BY_TICKER.get(ticker.upper())
    if table is None:
        return 50, "brak danych sezonowych dla tego instrumentu"

    month = _dt.datetime.now().month
    modifier = table.get(month, 0)
    score = float(np.clip(50 + modifier, 0, 100))

    if modifier > 0:
        note = f"miesiąc historycznie sprzyjający dla tego surowca (+{modifier} pkt)"
    elif modifier < 0:
        note = f"miesiąc historycznie słabszy dla tego surowca ({modifier} pkt)"
    else:
        note = "miesiąc neutralny sezonowo dla tego surowca"

    return score, note


def score_valuation(info: dict) -> tuple[float, str]:
    pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    peg = info.get("pegRatio")

    if pe is None:
        return 50, "brak danych P/E (możliwe straty / brak danych)"

    notes = [f"P/E={pe:.1f}"]
    score = 50

    # bardzo prosta heurystyka - edytuj progi według własnej oceny branży
    if pe < 15:
        score += 20
        notes.append("niskie P/E")
    elif pe > 40:
        score -= 20
        notes.append("wysokie P/E")

    if forward_pe and forward_pe < pe:
        score += 10
        notes.append(f"forward P/E={forward_pe:.1f} (oczekiwany wzrost zysków)")
    elif forward_pe and forward_pe > pe:
        score -= 5
        notes.append(f"forward P/E={forward_pe:.1f} (oczekiwany spadek zysków)")

    if peg:
        notes.append(f"PEG={peg:.2f}")
        if peg < 1:
            score += 10
        elif peg > 2:
            score -= 10

    return float(np.clip(score, 0, 100)), ", ".join(notes)


def score_dividend(info: dict) -> tuple[float, str]:
    yield_pct = info.get("dividendYield")
    payout = info.get("payoutRatio")

    if not yield_pct:
        return 50, "spółka nie płaci dywidendy"

    yield_pct = yield_pct * 100 if yield_pct < 1 else yield_pct
    notes = [f"yield={yield_pct:.2f}%"]
    score = 50

    if 1 <= yield_pct <= 6:
        score += 15
        notes.append("rozsądna stopa dywidendy")
    elif yield_pct > 8:
        score -= 15
        notes.append("bardzo wysoka stopa - sprawdź czy bezpieczna")

    if payout is not None:
        notes.append(f"payout ratio={payout:.0%}")
        if payout > 1:
            score -= 15
            notes.append("firma wypłaca więcej niż zarabia")
        elif payout < 0.7:
            score += 5

    return float(np.clip(score, 0, 100)), ", ".join(notes)


def score_fundamentals_deep(info: dict) -> tuple[float, str]:
    """
    Głębsze fundamenty: wzrost przychodów, rentowność (ROE), zadłużenie
    (debt/equity) i wolne przepływy pieniężne (free cash flow).
    Każdy dostępny element wpływa na wynik; brakujące dane są pomijane
    (nie karane), żeby nie zaniżać wyniku spółkom, dla których Yahoo
    nie udostępnia pełnych danych.
    """
    score = 50.0
    notes = []
    found_any = False

    revenue_growth = info.get("revenueGrowth")
    if revenue_growth is not None:
        found_any = True
        pct = revenue_growth * 100
        notes.append(f"wzrost przychodów r/r={pct:.1f}%")
        if pct > 15:
            score += 12
        elif pct > 5:
            score += 6
        elif pct < -5:
            score -= 12
        elif pct < 0:
            score -= 6

    roe = info.get("returnOnEquity")
    if roe is not None:
        found_any = True
        pct = roe * 100
        notes.append(f"ROE={pct:.1f}%")
        if pct > 15:
            score += 10
        elif pct > 8:
            score += 4
        elif pct < 0:
            score -= 10

    debt_to_equity = info.get("debtToEquity")
    if debt_to_equity is not None:
        found_any = True
        notes.append(f"dług/kapitał={debt_to_equity:.0f}%")
        if debt_to_equity > 200:
            score -= 12
        elif debt_to_equity > 100:
            score -= 5
        elif debt_to_equity < 30:
            score += 5

    fcf = info.get("freeCashflow")
    market_cap = info.get("marketCap")
    if fcf is not None:
        found_any = True
        if fcf > 0:
            notes.append("dodatni wolny cash flow")
            score += 8
            if market_cap and market_cap > 0:
                fcf_yield = fcf / market_cap * 100
                notes.append(f"FCF yield={fcf_yield:.1f}%")
        else:
            notes.append("ujemny wolny cash flow (firma 'spala' gotówkę)")
            score -= 8

    if not found_any:
        return 50, "brak wystarczających danych fundamentalnych"

    return float(np.clip(score, 0, 100)), ", ".join(notes)


def detect_red_flags(info: dict) -> list[str]:
    """
    Lista ostrzeżeń ("red flags") w prostym języku - sytuacje, na które
    warto zwrócić uwagę przed inwestycją. To NIE są automatyczne "nie kupuj",
    tylko sygnały do dalszego sprawdzenia.
    """
    flags = []

    revenue_growth = info.get("revenueGrowth")
    if revenue_growth is not None and revenue_growth < -0.10:
        flags.append(
            f"📉 Przychody spadają o {abs(revenue_growth)*100:.0f}% rok do roku - "
            "warto sprawdzić, czy to tymczasowe, czy długoterminowy trend."
        )

    debt_to_equity = info.get("debtToEquity")
    if debt_to_equity is not None and debt_to_equity > 200:
        flags.append(
            f"💳 Wysokie zadłużenie względem kapitału własnego ({debt_to_equity:.0f}%) - "
            "firma może być bardziej wrażliwa na wysokie stopy procentowe."
        )

    fcf = info.get("freeCashflow")
    if fcf is not None and fcf < 0:
        flags.append(
            "💸 Firma ma ujemny wolny cash flow - wydaje więcej gotówki, "
            "niż generuje z działalności."
        )

    payout = info.get("payoutRatio")
    if payout is not None and payout > 1:
        flags.append(
            f"💰 Firma wypłaca w dywidendach więcej niż zarabia (payout ratio={payout:.0%}) - "
            "dywidenda może być w przyszłości obniżona."
        )

    pe = info.get("trailingPE")
    profit_margin = info.get("profitMargins")
    if pe is not None and pe > 60:
        flags.append(
            f"🔥 Bardzo wysokie P/E ({pe:.0f}) - rynek wycenia bardzo wysoki "
            "przyszły wzrost; ryzyko dużego spadku przy rozczarowaniu wynikami."
        )
    if profit_margin is not None and profit_margin < 0:
        flags.append(
            f"🩸 Firma jest nierentowna (marża zysku={profit_margin:.0%})."
        )

    short_pct = info.get("shortPercentOfFloat")
    if short_pct is not None and short_pct > 0.15:
        flags.append(
            f"🎯 Wysoki udział krótkich pozycji ({short_pct:.0%} akcji w obrocie) - "
            "spora część rynku obstawia spadek ceny."
        )

    return flags


def fetch_news(stock) -> list[dict]:
    """Pobiera surową listę newsów z yfinance (z obsługą błędów)."""
    try:
        return stock.news or []
    except Exception:
        return []


def get_news_list(news: list[dict], limit: int = 5) -> list[dict]:
    """
    Zwraca uproszczoną listę newsów do wyświetlenia w UI:
    [{title, link, publisher, published}, ...]
    Obsługuje stary i nowy format odpowiedzi yfinance.
    """
    out = []
    for item in news[:limit]:
        content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        title = item.get("title") or content.get("title")
        if not title:
            continue

        link = item.get("link") or content.get("canonicalUrl", {}).get("url") \
            or content.get("clickThroughUrl", {}).get("url")

        publisher = item.get("publisher") or content.get("provider", {}).get("displayName", "")

        published_raw = item.get("providerPublishTime") or content.get("pubDate")
        published = ""
        if isinstance(published_raw, (int, float)):
            try:
                published = pd.to_datetime(published_raw, unit="s").strftime("%Y-%m-%d %H:%M")
            except Exception:
                published = ""
        elif isinstance(published_raw, str):
            try:
                published = pd.to_datetime(published_raw).strftime("%Y-%m-%d %H:%M")
            except Exception:
                published = published_raw

        out.append({
            "title": title,
            "link": link or "",
            "publisher": publisher or "",
            "published": published,
        })
    return out


@with_backoff(times=2, base_delay=1.0)
def get_calendar_info(stock) -> dict:
    """
    Zwraca informacje o najbliższych wydarzeniach: dacie wyników
    finansowych (earnings) i dacie "ex-dividend" (jeśli dostępne).
    Wartości to stringi ISO (YYYY-MM-DD) lub None.
    """
    earnings_date = None
    ex_dividend_date = None

    try:
        cal = stock.calendar
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, (list, tuple)) and ed:
                earnings_date = pd.Timestamp(ed[0]).date().isoformat()
            elif ed is not None:
                earnings_date = pd.Timestamp(ed).date().isoformat()

            exd = cal.get("Ex-Dividend Date")
            if exd is not None:
                ex_dividend_date = pd.Timestamp(exd).date().isoformat()
        elif cal is not None and not cal.empty:
            # starszy format - DataFrame
            if "Earnings Date" in cal.index:
                val = cal.loc["Earnings Date"].iloc[0]
                earnings_date = pd.Timestamp(val).date().isoformat()
    except Exception:
        pass

    if ex_dividend_date is None:
        try:
            divs = stock.dividends
            if divs is not None and not divs.empty:
                last_div_date = divs.index[-1]
                # szacunek: następna dywidenda ~rok po ostatniej (kwartalnie
                # bywa częściej, ale to tylko orientacyjna informacja)
                ex_dividend_date = last_div_date.date().isoformat() + " (ostatnia; harmonogram orientacyjny)"
        except Exception:
            pass

    return {"earnings_date": earnings_date, "ex_dividend_date": ex_dividend_date}


def score_sentiment(news: list[dict]) -> tuple[float, str]:
    """
    Bardzo prosty sentiment na podstawie tytułów ostatnich newsów -
    słownikowe liczenie słów pozytywnych/negatywnych. To uproszczenie,
    nie pełny NLP, ale daje orientacyjny sygnał.

    `news`: surowa lista z yfinance (stock.news), patrz fetch_news().
    """
    POSITIVE_WORDS = {
        "surge", "soar", "jump", "gain", "rise", "rises", "rising", "up",
        "beat", "beats", "record", "growth", "strong", "boost", "rally",
        "upgrade", "outperform", "buy", "bullish", "profit", "exceeds",
        "win", "wins", "positive", "high", "higher", "best",
    }
    NEGATIVE_WORDS = {
        "fall", "falls", "falling", "drop", "drops", "plunge", "slump",
        "down", "miss", "misses", "loss", "losses", "weak", "cut", "cuts",
        "downgrade", "underperform", "sell", "bearish", "decline",
        "warning", "lawsuit", "investigation", "recall", "low", "lower",
        "worst", "risk", "concern", "concerns",
    }

    if not news:
        return 50, "brak dostępnych newsów"

    pos, neg, total_words = 0, 0, 0
    titles_checked = 0

    for item in news[:10]:
        content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        title = item.get("title") or content.get("title", "")
        if not title:
            continue
        titles_checked += 1
        words = title.lower().replace(",", " ").replace(".", " ").split()
        for w in words:
            w = w.strip("'\"():")
            if w in POSITIVE_WORDS:
                pos += 1
            elif w in NEGATIVE_WORDS:
                neg += 1
            total_words += 1

    if titles_checked == 0:
        return 50, "brak tytułów newsów do analizy"

    if pos + neg == 0:
        return 50, f"przeanalizowano {titles_checked} nagłówków, neutralny ton"

    ratio = pos / (pos + neg)
    score = 50 + (ratio - 0.5) * 80  # mapuje 0..1 -> ~10..90
    score = float(np.clip(score, 0, 100))

    return score, f"{titles_checked} nagłówków: {pos} pozytywnych słów, {neg} negatywnych"


def compute_simple_score_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Liczy uproszczony 'techniczny score' (na bazie RSI, trendu MA i MACD)
    dla KAŻDEGO dnia w historii (wektorowo - szybkie nawet dla lat danych).
    Używane do wykresu 'historia sygnału' oraz do backtestingu.

    Zwraca DataFrame z kolumnami: Date, Score, Close
    """
    work = df.copy()
    # usuń wiersze bez pełnych danych (np. pierwsze 200 dni bez MA200/RSI)
    valid = work.dropna(subset=["RSI", "MA50", "MA200", "MACD", "MACD_signal"])

    rsi_val = valid["RSI"]
    s_rsi = np.where(rsi_val <= 30, 80, np.where(rsi_val >= 70, 20, 100 - rsi_val))

    price, ma50, ma200 = valid["Close"], valid["MA50"], valid["MA200"]
    s_trend = (
        50
        + np.where(price > ma50, 15, -15)
        + np.where(price > ma200, 15, -15)
        + np.where(ma50 > ma200, 10, -10)
    )
    s_trend = np.clip(s_trend, 0, 100)

    s_macd = np.where(valid["MACD"] > valid["MACD_signal"], 65, 35)

    simple_score = s_rsi * 0.35 + s_trend * 0.45 + s_macd * 0.20

    return pd.DataFrame({
        "Date": valid.index,
        "Score": np.round(simple_score, 1),
        "Close": valid["Close"].values,
    }).reset_index(drop=True)


def score_momentum(df: pd.DataFrame) -> tuple[float, str]:
    close = df["Close"]
    if len(close) < 22:
        return 50, "brak danych"

    chg_1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100
    chg_3m = (close.iloc[-1] / close.iloc[-66] - 1) * 100 if len(close) >= 66 else None

    score = 50 + np.clip(chg_1m, -25, 25)  # +/-25% mapuje na +/-25 punktów
    note = f"zmiana 1M={chg_1m:.1f}%"
    if chg_3m is not None:
        note += f", 3M={chg_3m:.1f}%"

    return float(np.clip(score, 0, 100)), note


# ----------------------------------------------------------------------
# GŁÓWNA ANALIZA
# ----------------------------------------------------------------------
def analyze_ticker(ticker: str) -> dict:
    ticker = sanitize_ticker(ticker)
    if not ticker:
        return {"ticker": ticker, "error": "Pusty lub nieprawidłowy symbol."}

    stock = yf.Ticker(ticker)
    try:
        df = fetch_history(stock, period=PERIOD, interval=INTERVAL)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return {"ticker": ticker, "error": "Brak danych - sprawdź symbol (Yahoo Finance może też mieć chwilowy problem - spróbuj ponownie za chwilę)"}

    # Usuń wiersze z NaN ceną zamknięcia (yfinance czasem dodaje dzisiejszy
    # niekompletny wiersz, gdzie Close = NaN, co psuje wszystkie wskaźniki).
    df = df.dropna(subset=["Close"])
    if df.empty:
        return {"ticker": ticker, "error": "Brak prawidłowych danych cenowych."}

    # wskaźniki
    df["RSI"] = rsi(df["Close"])
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = macd(df["Close"])
    df["BB_mid"], df["BB_upper"], df["BB_lower"] = bollinger_bands(df["Close"])

    info = fetch_info(stock)
    news = fetch_news(stock)

    asset_type = get_asset_type(info, ticker=ticker)
    weights = get_weights_for_asset_type(asset_type)

    all_components = {
        "rsi": score_rsi(df),
        "trend_ma": score_trend_ma(df),
        "macd": score_macd(df),
        "volume": score_volume(df),
        "volatility": score_volatility(df),
        "valuation": score_valuation(info),
        "momentum": score_momentum(df),
        "dividend": score_dividend(info),
        "sentiment": score_sentiment(news),
        "fundamentals": score_fundamentals_deep(info),
    }
    # Składowe specjalistyczne - liczone tylko gdy faktycznie potrzebne
    # (czyli gdy występują w wagach dla danego typu aktywa), żeby nie
    # wykonywać zbędnej pracy (np. score_btc_dominance robi dodatkowe
    # zapytanie sieciowe dla BTC) dla instrumentów, które ich nie używają.
    if "volatility_crypto" in weights:
        all_components["volatility_crypto"] = score_volatility_crypto(df)
    if "btc_dominance" in weights:
        all_components["btc_dominance"] = score_btc_dominance(ticker, df)
    if "seasonality" in weights:
        all_components["seasonality"] = score_seasonality(ticker)

    # tylko składowe sensowne dla tego typu aktywa (patrz weights powyżej)
    components = {k: v for k, v in all_components.items() if k in weights}

    total_score = sum(components[k][0] * weights[k] for k in weights)

    # Zabezpieczenie: jeśli któryś komponent zwrócił NaN (błąd w danych),
    # total_score też będzie NaN. Zamiast propagować błąd, wróć do neutral.
    if np.isnan(total_score):
        total_score = 50.0

    last_price = df["Close"].iloc[-1]
    if np.isnan(last_price):
        return {"ticker": ticker, "error": "Brak prawidłowej ceny zamknięcia."}

    # info.get("sector") bywa None (krypto, surowce, część ETF), więc zwykły
    # default w .get() nie wystarcza. Dla takich aktywów użyj sensownej etykiety.
    sector = info.get("sector") or None
    if not sector:
        if asset_type == "crypto":
            sector = "Kryptowaluta"
        elif asset_type in ("commodity", "etf_commodity"):
            sector = ASSET_TYPE_LABELS.get(asset_type, "Surowiec / kontrakt")
        elif asset_type == "etf":
            sector = info.get("category") or "ETF"
        else:
            sector = "Nieznany"
    pe = info.get("trailingPE")

    try:
        beta_info = compute_beta(ticker, df)
    except Exception:
        beta_info = None

    try:
        relative_strength = compute_relative_strength(ticker, df)
    except Exception:
        relative_strength = None

    try:
        ma_crossover = detect_ma_crossover(df)
    except Exception:
        ma_crossover = None

    try:
        calendar_info = get_calendar_info(stock)
    except Exception:
        calendar_info = {"earnings_date": None, "ex_dividend_date": None}

    return {
        "ticker": ticker,
        "price": round(float(last_price), 2),
        "total_score": round(total_score, 1),
        "components": components,
        "weights": weights,
        "asset_type": asset_type,
        "asset_type_label": ASSET_TYPE_LABELS.get(asset_type, "Inny instrument"),
        "currency": info.get("currency", "?"),
        "name": info.get("longName") or info.get("shortName", ticker),
        "sector": sector,
        "industry": info.get("industry", "Nieznana"),
        "category": info.get("category"),         # kategoria funduszu (ETF)
        "fund_family": info.get("fundFamily"),     # dostawca ETF (ETF)
        "sector_pe_comparison": compare_to_sector_pe(pe, sector) if asset_type == "stock" else None,
        "beta_info": beta_info,
        "relative_strength": relative_strength,
        "ma_crossover": ma_crossover,
        "vwap": vwap_position(df),
        "red_flags": detect_red_flags(info) if asset_type == "stock" else [],
        "news_list": get_news_list(news),
        "calendar_info": calendar_info,
    }


def interpret_score(score: float) -> str:
    if score >= 70:
        return "SILNY SYGNAŁ POZYTYWNY"
    if score >= 60:
        return "Sygnał umiarkowanie pozytywny"
    if score >= 40:
        return "Neutralnie"
    if score >= 30:
        return "Sygnał umiarkowanie negatywny"
    return "SILNY SYGNAŁ NEGATYWNY"


def print_report(result: dict):
    if "error" in result:
        print(f"\n{result['ticker']}: {result['error']}")
        return

    print(f"\n{'='*60}")
    print(f"{result['name']} ({result['ticker']}) - {result.get('asset_type_label', 'Akcja')}")
    print(f"Cena: {result['price']} {result['currency']}")
    print(f"{'='*60}")
    print(f"SCORE OGÓLNY: {result['total_score']}/100 -> {interpret_score(result['total_score'])}")
    print(f"{'-'*60}")
    print("Rozbicie sygnałów:")
    weights = result.get("weights", WEIGHTS)
    for key, (val, note) in result["components"].items():
        weight = weights[key]
        print(f"  {key:12s} | {val:5.1f}/100 (waga {weight:.0%}) | {note}")
    print(f"{'='*60}")


# ----------------------------------------------------------------------
def main():
    tickers = sys.argv[1:]
    if not tickers:
        tickers = ["AAPL", "MSFT"]
        print("(brak argumentów - przykład dla AAPL, MSFT)")
        print("Użycie: python stock_analyzer.py TICKER1 TICKER2 ...")

    results = []
    for t in tickers:
        try:
            res = analyze_ticker(t)
            print_report(res)
            results.append(res)
        except Exception as e:
            print(f"\n{t}: błąd - {e}")

    # ranking jeśli więcej niż 1 ticker
    valid = [r for r in results if "error" not in r]
    if len(valid) > 1:
        print(f"\n{'='*60}")
        print("RANKING (od najwyższego score):")
        for r in sorted(valid, key=lambda x: -x["total_score"]):
            print(f"  {r['ticker']:8s} {r['total_score']:6.1f}  {interpret_score(r['total_score'])}")

    print("\n--- DISCLAIMER ---")
    print("To narzędzie analityczne, nie porada inwestycyjna.")
    print("Score bazuje na uproszczonych wskaźnikach historycznych")
    print("i nie przewiduje przyszłych cen. Decyzje inwestycyjne")
    print("podejmuj na własną odpowiedzialność / konsultuj z doradcą.")


if __name__ == "__main__":
    main()
