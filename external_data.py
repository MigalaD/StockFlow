# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Klienci darmowych API danych rynkowych: Binance, CoinGecko, Alpaca
====================================================================
Uzupełniają Yahoo Finance o dane bliższe rzeczywistemu "live":

- Binance: prawdziwe ceny real-time dla kryptowalut (REST, brak rejestracji).
  Używane jako podstawowe źródło ceny na stronie Krypto - Yahoo zostaje
  zapasowym źródłem (fallback), gdyby Binance było niedostępne.
- CoinGecko: dominacja BTC (% udziału Bitcoina w całym rynku krypto) -
  potrzebne do score_btc_dominance() w stock_analyzer.py.
- Alpaca Markets: darmowe dane (paper trading, bez karty) dla amerykańskich
  akcji/ETF-ów jako uzupełnienie Yahoo. Wymaga klucza API (darmowy, ale
  trzeba go wygenerować na alpaca.markets) - bez klucza moduł degraduje
  się do "niedostępne", aplikacja korzysta wtedy z samego Yahoo.

WAŻNE - uczciwość względem "live": Binance i Alpaca dają prawdziwe dane
bieżące (sekundy), ale tylko dla swoich rynków (Binance = krypto, Alpaca =
giełdy USA). GPW i rynki europejskie nadal korzystają wyłącznie z Yahoo
Finance (~15 min opóźnienia) - nie ma dla nich darmowego źródła real-time.

Wszystkie funkcje są zaprojektowane tak, by NIGDY nie wywalić aplikacji:
przy błędzie sieci/API zwracają None, a wywołujący kod ma używać Yahoo
jako fallback.
"""
from __future__ import annotations

import os
import time
import threading

import requests

from app_logging import get_logger
from rate_limiter import rate_limited, with_backoff

log = get_logger("external_data")

_TIMEOUT = 5  # sekund - źródła pomocnicze nie mogą blokować strony na długo

# ----------------------------------------------------------------------
# BINANCE - ceny krypto w czasie rzeczywistym
# ----------------------------------------------------------------------
_BINANCE_BASE = "https://api.binance.com/api/v3"

# Mapowanie naszych tickerów (format Yahoo: BTC-USD) na symbole Binance
# (format: BTCUSDT). Binance notuje w USDT (stablecoin), nie czystym USD,
# ale różnica cenowa jest pomijalna (zwykle < 0.1%).
_BINANCE_SYMBOL_MAP = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT",
    "XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",
    "AVAX-USD": "AVAXUSDT",
    "DOT-USD": "DOTUSDT",
}


def binance_symbol_for(ticker: str) -> str | None:
    """Mapuje ticker Yahoo (BTC-USD) na symbol Binance (BTCUSDT), albo None."""
    return _BINANCE_SYMBOL_MAP.get(ticker.upper())


@with_backoff(times=2, base_delay=0.5)
@rate_limited
def _binance_get(path: str, params: dict | None = None) -> dict | list | None:
    try:
        resp = requests.get(f"{_BINANCE_BASE}{path}", params=params, timeout=_TIMEOUT)
        if resp.status_code != 200:
            log.warning("Binance HTTP %s dla %s", resp.status_code, path)
            return None
        return resp.json()
    except requests.RequestException as e:
        log.warning("Binance request error: %s", e)
        return None


def get_binance_price(ticker: str) -> dict | None:
    """Zwraca aktualną cenę live z Binance dla danego tickera (format Yahoo).

    Zwraca {price, change_24h_pct, volume_24h, high_24h, low_24h, source}
    albo None (gdy ticker nie jest obsługiwany lub API niedostępne).
    """
    symbol = binance_symbol_for(ticker)
    if not symbol:
        return None

    data = _binance_get("/ticker/24hr", params={"symbol": symbol})
    if not data or not isinstance(data, dict):
        return None

    try:
        return {
            "price": float(data["lastPrice"]),
            "change_24h_pct": float(data["priceChangePercent"]),
            "volume_24h": float(data["volume"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"]),
            "source": "Binance (live)",
            "timestamp": time.time(),
        }
    except (KeyError, ValueError, TypeError) as e:
        log.warning("Binance: nieoczekiwany format odpowiedzi: %s", e)
        return None


def get_binance_klines(ticker: str, interval: str = "1d", limit: int = 200):
    """Pobiera świece (OHLCV) z Binance - format zgodny z pandas DataFrame.

    interval: '1m', '5m', '15m', '1h', '4h', '1d' (interwały Binance).
    Zwraca listę list [open_time, open, high, low, close, volume, ...]
    albo None. Surowe dane - konwersja do DataFrame po stronie wołającego,
    żeby uniknąć twardej zależności pandas w tym module dla prostych wywołań.
    """
    symbol = binance_symbol_for(ticker)
    if not symbol:
        return None
    data = _binance_get("/klines", params={
        "symbol": symbol, "interval": interval, "limit": limit,
    })
    if not data or not isinstance(data, list):
        return None
    return data


def is_binance_supported(ticker: str) -> bool:
    """Czy dany ticker ma odpowiednik na Binance (do warunkowego UI)."""
    return binance_symbol_for(ticker) is not None


def binance_klines_to_df(klines: list) -> "pd.DataFrame | None":
    """Konwertuje surowe świece Binance (lista list) do DataFrame kompatybilnego
    z formatem Yahoo Finance (kolumny Open/High/Low/Close/Volume, indeks datetime).

    Format jednej świecy Binance:
    [open_time_ms, open, high, low, close, volume, close_time_ms, ...]

    Zwraca None gdy klines jest pusty lub nastąpił błąd parsowania.
    """
    if not klines:
        return None
    try:
        import pandas as pd
        import numpy as np
        rows = []
        for k in klines:
            rows.append({
                "Open":   float(k[1]),
                "High":   float(k[2]),
                "Low":    float(k[3]),
                "Close":  float(k[4]),
                "Volume": float(k[5]),
            })
        # Indeks: open_time w milisekundach → datetime UTC → naive (bez tz) jak Yahoo
        timestamps = pd.to_datetime([k[0] for k in klines], unit="ms", utc=True)
        timestamps = timestamps.tz_localize(None)
        df = pd.DataFrame(rows, index=timestamps)
        df = df.dropna(subset=["Close"])
        return df if not df.empty else None
    except Exception:
        return None


# ----------------------------------------------------------------------
# COINGECKO - dominacja BTC i dane rynku krypto
# ----------------------------------------------------------------------
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"


@with_backoff(times=2, base_delay=1.0)
@rate_limited
def _coingecko_get(path: str, params: dict | None = None) -> dict | None:
    try:
        resp = requests.get(f"{_COINGECKO_BASE}{path}", params=params, timeout=_TIMEOUT)
        if resp.status_code != 200:
            log.warning("CoinGecko HTTP %s dla %s", resp.status_code, path)
            return None
        return resp.json()
    except requests.RequestException as e:
        log.warning("CoinGecko request error: %s", e)
        return None


def get_btc_dominance() -> dict | None:
    """Zwraca aktualną dominację BTC (% kapitalizacji całego rynku krypto).

    {btc_dominance_pct, eth_dominance_pct, total_market_cap_usd} albo None.
    """
    data = _coingecko_get("/global")
    if not data or "data" not in data:
        return None
    try:
        d = data["data"]
        return {
            "btc_dominance_pct": round(float(d["market_cap_percentage"]["btc"]), 2),
            "eth_dominance_pct": round(float(d["market_cap_percentage"].get("eth", 0)), 2),
            "total_market_cap_usd": float(d["total_market_cap"]["usd"]),
            "market_cap_change_24h_pct": round(float(d.get("market_cap_change_percentage_24h_usd", 0)), 2),
        }
    except (KeyError, ValueError, TypeError) as e:
        log.warning("CoinGecko: nieoczekiwany format /global: %s", e)
        return None


# ----------------------------------------------------------------------
# ALPACA MARKETS - dane dla akcji/ETF-ów USA (wymaga darmowego klucza API)
# ----------------------------------------------------------------------
_ALPACA_DATA_BASE = "https://data.alpaca.markets/v2"


def _alpaca_credentials() -> tuple[str, str] | None:
    """Pobiera klucz/sekret Alpaca z (kolejno): st.secrets, zmiennych
    środowiskowych. Brak konfiguracji -> None (moduł milcząco degraduje
    się do braku tego źródła, Yahoo pozostaje głównym źródłem dla USA).
    """
    try:
        import streamlit as st
        if "ALPACA_API_KEY" in st.secrets and "ALPACA_SECRET_KEY" in st.secrets:
            return str(st.secrets["ALPACA_API_KEY"]), str(st.secrets["ALPACA_SECRET_KEY"])
    except Exception:
        pass

    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if key and secret:
        return key, secret
    return None


def is_alpaca_configured() -> bool:
    return _alpaca_credentials() is not None


@with_backoff(times=2, base_delay=0.5)
@rate_limited
def _alpaca_get(path: str, params: dict | None = None) -> dict | None:
    creds = _alpaca_credentials()
    if not creds:
        return None
    key, secret = creds
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        resp = requests.get(
            f"{_ALPACA_DATA_BASE}{path}", params=params, headers=headers, timeout=_TIMEOUT
        )
        if resp.status_code != 200:
            log.warning("Alpaca HTTP %s dla %s", resp.status_code, path)
            return None
        return resp.json()
    except requests.RequestException as e:
        log.warning("Alpaca request error: %s", e)
        return None


def get_alpaca_quote(ticker: str) -> dict | None:
    """Najnowszy quote (bid/ask) z Alpaca dla amerykańskiej akcji/ETF-u.

    Zwraca {price, bid, ask, source, timestamp} albo None (np. brak klucza
    API, ticker spoza USA, lub błąd sieci). Cena = midpoint bid/ask.
    """
    ticker = ticker.upper().strip()
    if not ticker.isalnum():
        return None  # Alpaca obsługuje tylko proste symbole USA (bez .WA, -USD itp.)

    data = _alpaca_get(f"/stocks/{ticker}/quotes/latest")
    if not data or "quote" not in data:
        return None
    try:
        q = data["quote"]
        bid, ask = float(q["bp"]), float(q["ap"])
        if bid <= 0 or ask <= 0:
            return None
        return {
            "price": round((bid + ask) / 2, 4),
            "bid": bid,
            "ask": ask,
            "source": "Alpaca (live)",
            "timestamp": q.get("t"),
        }
    except (KeyError, ValueError, TypeError) as e:
        log.warning("Alpaca: nieoczekiwany format quote: %s", e)
        return None


def is_alpaca_supported(ticker: str) -> bool:
    """Heurystyka: Alpaca obsługuje tylko proste symbole USA (litery, bez
    kropek/myślników) - wyklucza GPW (.WA), Europę (.DE/.L/...), krypto (-USD).
    Nie gwarantuje, że dany ticker faktycznie istnieje na Alpaca - tylko że
    ma poprawny format do sprawdzenia.
    """
    t = ticker.upper().strip()
    return t.isalnum() and 1 <= len(t) <= 5


# Mapowanie interwałów aplikacji -> timeframe Alpaca
_ALPACA_TIMEFRAMES = {
    "1m":  "1Min",
    "5m":  "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h":  "1Hour",
    "1d":  "1Day",
}


def get_alpaca_bars(ticker: str, interval: str = "1d", limit: int = 365) -> list[dict] | None:
    """Pobiera historyczne bary OHLCV z Alpaca dla akcji/ETF-u USA (live, IEX feed).

    Zwraca listę dict {timestamp, open, high, low, close, volume} albo None
    (brak klucza, ticker spoza USA, błąd). Używa darmowego feedu IEX.

    WAŻNE: Alpaca wymaga jawnego parametru `start`, inaczej zwraca tylko
    najnowszą dostępną świecę zamiast pełnej historii (mimo ustawionego limit).
    """
    ticker = ticker.upper().strip()
    if not is_alpaca_supported(ticker):
        return None
    if not is_alpaca_configured():
        return None

    timeframe = _ALPACA_TIMEFRAMES.get(interval, "1Day")

    # Oblicz `start` tak, by zmieścić `limit` świec danego interwału.
    # Mnożnik z zapasem (weekendy/święta dla danych dziennych, przerwy sesji dla intraday).
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    minutes_per_bar = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "1d": 60 * 24,
    }.get(interval, 60 * 24)

    if interval == "1d":
        # Dane dzienne: dni kalendarzowe z zapasem na weekendy (~1.5x)
        lookback_days = int(limit * 1.6) + 5
    else:
        # Dane intraday: giełda USA otwarta ~6.5h/dzień -> ~390 min/dzień
        bars_per_trading_day = max(1, 390 // minutes_per_bar)
        lookback_days = int(limit / bars_per_trading_day * 1.6) + 5
        lookback_days = max(lookback_days, 2)

    start = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "timeframe":  timeframe,
        "start":      start,
        "limit":      min(limit, 1000),
        "feed":       "iex",        # darmowy feed (SIP wymaga płatnej subskrypcji)
        "adjustment": "raw",
        "sort":       "asc",        # rosnąco po czasie (wykres oczekuje chronologii)
    }

    data = _alpaca_get(f"/stocks/{ticker}/bars", params=params)
    if not data or "bars" not in data or not data["bars"]:
        return None

    try:
        bars = []
        for b in data["bars"]:
            bars.append({
                "timestamp": b["t"],                 # ISO 8601 string
                "open":      float(b["o"]),
                "high":      float(b["h"]),
                "low":       float(b["l"]),
                "close":     float(b["c"]),
                "volume":    float(b["v"]),
            })
        return bars
    except (KeyError, ValueError, TypeError) as e:
        log.warning("Alpaca: nieoczekiwany format bars: %s", e)
        return None
