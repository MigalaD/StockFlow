# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /analyze
  GET /analyze/{ticker}           — pełna analiza (score DT + ST, składowe)
  GET /analyze/{ticker}/history   — historia score (ostatnie N dni)
  GET /analyze/{ticker}/signals   — sygnały krótkoterminowe (ATR, Stochastik, OBV, S/R)
  GET /analyze/{ticker}/candles   — dane OHLCV (1d/1h/30m/15m/5m/1m)
  GET /analyze/search             — wyszukiwanie tickerów po nazwie
"""

from __future__ import annotations

import sys
import os
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from stock_analyzer import analyze_ticker, search_tickers
from intraday_signals import (
    atr_summary,
    compute_obv,
    compute_stochastic,
    detect_obv_divergence,
    detect_support_resistance,
    stochastic_summary,
)
import external_data
from backend.core.security import OptionalCurrentUser
from backend.models.schemas import (
    AnalysisResponse,
    ComponentItem,
    MarketDataResponse,
    OHLCVItem,
    ScoreHistoryItem,
)

router = APIRouter(prefix="/analyze", tags=["analysis"])

# Mapowanie interwałów — te same co w common.py Streamlit
_INTERVALS = {
    "1d":  {"yf": "1d",  "period": "1y",  "binance": "1d",  "limit": 365},
    "1h":  {"yf": "1h",  "period": "60d", "binance": "1h",  "limit": 500},
    "30m": {"yf": "30m", "period": "30d", "binance": "30m", "limit": 500},
    "15m": {"yf": "15m", "period": "8d",  "binance": "15m", "limit": 500},
    "5m":  {"yf": "5m",  "period": "5d",  "binance": "5m",  "limit": 500},
    "1m":  {"yf": "1m",  "period": "7d",  "binance": "1m",  "limit": 500},
}


def _components_to_list(components: dict, weights: dict) -> list[ComponentItem]:
    result = []
    for key, (score, note) in components.items():
        result.append(ComponentItem(
            key    = key,
            score  = round(float(score), 1),
            note   = note,
            weight = round(float(weights.get(key, 0)), 4),
        ))
    return result


def _compute_overlays(closes: list[float]) -> dict:
    """Oblicza Bollinger Bands (20,2) + MA50/MA200 dla listy cen zamknięcia.
    Zwraca dict z listami (None gdy za mało danych w danym punkcie)."""
    import statistics
    n = len(closes)
    bb_u, bb_m, bb_l, ma50, ma200 = [], [], [], [], []
    for i in range(n):
        # Bollinger 20
        if i >= 19:
            window = closes[i-19:i+1]
            mean = sum(window) / 20
            std  = statistics.pstdev(window)
            bb_m.append(round(mean, 4))
            bb_u.append(round(mean + 2*std, 4))
            bb_l.append(round(mean - 2*std, 4))
        else:
            bb_m.append(None); bb_u.append(None); bb_l.append(None)
        # MA50
        if i >= 49:
            ma50.append(round(sum(closes[i-49:i+1]) / 50, 4))
        else:
            ma50.append(None)
        # MA200
        if i >= 199:
            ma200.append(round(sum(closes[i-199:i+1]) / 200, 4))
        else:
            ma200.append(None)
    return {"bb_upper": bb_u, "bb_middle": bb_m, "bb_lower": bb_l, "ma50": ma50, "ma200": ma200}


@router.get(
    "/search",
    summary="Search tickers",
    description="Wyszukuje tickery po nazwie lub symbolu. Zwraca max 10 wyników.",
)
async def search(
    q:     str = Query(..., min_length=1, max_length=50, description="Fraza wyszukiwania"),
    limit: int = Query(8, ge=1, le=20),
    _user: OptionalCurrentUser = None,
) -> list[dict]:
    """
    Wyszukuje instrumenty finansowe.
    Nie wymaga uwierzytelnienia — publiczny endpoint.
    """
    try:
        results = search_tickers(q, limit=limit)
        return results or []
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Search unavailable: {e}")


@router.get(
    "/{ticker}",
    response_model=AnalysisResponse,
    summary="Full analysis",
    description=(
        "Pełna analiza instrumentu: score DT i ST, składowe, red flags, "
        "VWAP, crossover MA, beta, siła relatywna."
    ),
)
async def analyze(
    ticker: str,
    _user:  OptionalCurrentUser = None,
) -> AnalysisResponse:
    """
    Główny endpoint analizy. Wyniki są cache'owane po stronie klienta
    (nagłówek Cache-Control) — TTL zależny od rynku (GPW 15 min, crypto 60s).

    Endpoint publiczny — nie wymaga JWT.
    """
    ticker = ticker.strip().upper()
    try:
        result = analyze_ticker(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analysis failed: {e}",
        )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for ticker '{ticker}'",
        )

    # Oblicz zmianę dobową z ostatnich dwóch zamknięć (niezależnie od analyze_ticker)
    change_24h = None
    change_pct = None
    live_price = None
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if hist is not None and len(hist) >= 2:
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            if prev > 0:
                change_24h = round(last - prev, 2)
                change_pct = round((last - prev) / prev * 100, 2)
                # Live quote z Alpaca (US stocks) — nadpisz cenę najświeższą
                if external_data.is_alpaca_supported(ticker) and external_data.is_alpaca_configured():
                    q = external_data.get_alpaca_quote(ticker)
                    if q and q.get("price"):
                        live_price = round(float(q["price"]), 2)
                        change_24h = round(live_price - prev, 2)
                        change_pct = round((live_price - prev) / prev * 100, 2)
    except Exception:
        pass

    response = AnalysisResponse(
        ticker       = result["ticker"],
        name         = result.get("name", ticker),
        price        = live_price if live_price is not None else result.get("price", 0.0),
        currency     = result.get("currency", "USD"),
        change_24h   = change_24h,
        change_pct   = change_pct,
        total_score  = result.get("total_score", 50.0),
        score_st     = result.get("score_st"),
        asset_type   = result.get("asset_type", "stock"),
        sector       = result.get("sector"),
        industry     = result.get("industry"),
        components   = _components_to_list(
            result.get("components",    {}),
            result.get("weights",       {}),
        ),
        components_st = _components_to_list(
            result.get("components_st", {}),
            {},
        ),
        red_flags         = result.get("red_flags")    or [],
        vwap              = result.get("vwap"),
        ma_crossover      = result.get("ma_crossover"),
        beta_info         = result.get("beta_info"),
        relative_strength = result.get("relative_strength"),
    )

    # Zapisz score do historii (cicha — nie blokuje odpowiedzi)
    try:
        db.save_score_history(ticker, result["total_score"])
    except Exception:
        pass  # nie przerywaj analizy z powodu błędu zapisu historii

    return response


@router.get(
    "/{ticker}/history",
    response_model=list[ScoreHistoryItem],
    summary="Score history",
    description="Historia score DT dla danego tickera (ostatnie N dni).",
)
async def score_history(
    ticker: str,
    days:   int = Query(90, ge=7, le=365),
    _user:  OptionalCurrentUser = None,
) -> list[ScoreHistoryItem]:
    ticker = ticker.strip().upper()
    try:
        history = db.get_score_history(ticker, limit_days=days)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return [
        ScoreHistoryItem(date=row["day"], score=row["score"])
        for row in history
    ]


@router.get(
    "/{ticker}/signals",
    summary="Short-term signals",
    description=(
        "Sygnały krótkoterminowe: ATR ze stop-lossami, Stochastik %K/%D, "
        "OBV z dywergencją, poziomy wsparcia i oporu."
    ),
)
async def signals(
    ticker: str,
    period: str = Query("1y", description="Okres historii: 3mo | 6mo | 1y | 2y"),
    _user:  OptionalCurrentUser = None,
) -> dict:
    """
    Dane dla zakładki ⚡ Sygnały ST.
    Liczone na danych dziennych — narzędzie dla swing-tradingu.
    """
    ticker = ticker.strip().upper()
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        if df is None or df.empty:
            raise ValueError("No data")
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Data unavailable: {e}")

    try:
        atr_info   = atr_summary(df)
        stoch_info = stochastic_summary(df)
        obv_series = compute_obv(df)
        divergence = detect_obv_divergence(df)
        levels     = detect_support_resistance(df)

        k_series, d_series = compute_stochastic(df)

        return {
            "ticker":    ticker,
            "atr":       atr_info,
            "stochastic": {
                **( stoch_info or {} ),
                "k_series": [
                    {"date": str(d.date()), "value": round(float(v), 2)}
                    for d, v in zip(k_series.dropna().index[-60:],
                                    k_series.dropna().values[-60:])
                ],
                "d_series": [
                    {"date": str(d.date()), "value": round(float(v), 2)}
                    for d, v in zip(d_series.dropna().index[-60:],
                                    d_series.dropna().values[-60:])
                ],
            },
            "obv": {
                "divergence": divergence,
                "series": [
                    {"date": str(d.date()), "value": round(float(v), 0)}
                    for d, v in zip(obv_series.dropna().index[-120:],
                                    obv_series.dropna().values[-120:])
                ],
            },
            "levels": levels,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal computation failed: {e}")


@router.get(
    "/{ticker}/candles",
    response_model=MarketDataResponse,
    summary="OHLCV candles",
    description=(
        "Dane świecowe OHLCV dla wybranego interwału. "
        "Krypto: Binance (live, bez opóźnienia). "
        "Akcje/ETF: Yahoo Finance (~15 min opóźnienia)."
    ),
)
async def candles(
    ticker:   str,
    interval: Literal["1d", "1h", "30m", "15m", "5m", "1m"] = Query(
        "1d", description="Interwał świecy"
    ),
    overlays: bool = Query(True, description="Dołącz Bollinger Bands + MA50/200"),
    _user: OptionalCurrentUser = None,
) -> MarketDataResponse:
    ticker = ticker.strip().upper()
    cfg    = _INTERVALS.get(interval, _INTERVALS["1d"])

    def _attach_overlays(items: list[OHLCVItem]) -> list[OHLCVItem]:
        if not overlays or len(items) < 20:
            return items
        closes = [it.close for it in items]
        ov = _compute_overlays(closes)
        for i, it in enumerate(items):
            it.bb_upper  = ov["bb_upper"][i]
            it.bb_middle = ov["bb_middle"][i]
            it.bb_lower  = ov["bb_lower"][i]
            it.ma50      = ov["ma50"][i]
            it.ma200     = ov["ma200"][i]
        return items

    # Krypto: próbuj Binance (live)
    if external_data.is_binance_supported(ticker):
        klines = external_data.get_binance_klines(
            ticker, interval=cfg["binance"], limit=cfg["limit"]
        )
        if klines:
            candles_list = [
                OHLCVItem(
                    timestamp = str(k[0]),
                    open      = float(k[1]),
                    high      = float(k[2]),
                    low       = float(k[3]),
                    close     = float(k[4]),
                    volume    = float(k[5]),
                )
                for k in klines
            ]
            return MarketDataResponse(
                ticker   = ticker,
                interval = interval,
                source   = "Binance",
                candles  = _attach_overlays(candles_list),
                is_live  = True,
            )

    # Akcje/ETF USA: próbuj Alpaca (live, IEX feed) gdy skonfigurowane
    if external_data.is_alpaca_supported(ticker) and external_data.is_alpaca_configured():
        bars = external_data.get_alpaca_bars(
            ticker, interval=interval, limit=cfg["limit"]
        )
        if bars:
            candles_list = [
                OHLCVItem(
                    timestamp = b["timestamp"],
                    open      = b["open"],
                    high      = b["high"],
                    low       = b["low"],
                    close     = b["close"],
                    volume    = b["volume"],
                )
                for b in bars
            ]
            return MarketDataResponse(
                ticker   = ticker,
                interval = interval,
                source   = "Alpaca",
                candles  = _attach_overlays(candles_list),
                is_live  = True,
            )

    # Yahoo Finance fallback
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(
            period=cfg["period"], interval=cfg["yf"]
        )
        if df is None or df.empty:
            raise ValueError("No data from Yahoo")
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        candles_list = [
            OHLCVItem(
                timestamp = str(idx),
                open      = float(row["Open"]),
                high      = float(row["High"]),
                low       = float(row["Low"]),
                close     = float(row["Close"]),
                volume    = float(row["Volume"]),
            )
            for idx, row in df.iterrows()
            if not any(
                __import__("math").isnan(v)
                for v in [row["Open"], row["High"], row["Low"], row["Close"]]
            )
        ]
        return MarketDataResponse(
            ticker   = ticker,
            interval = interval,
            source   = "Yahoo Finance",
            candles  = _attach_overlays(candles_list),
            is_live  = False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Market data unavailable for {ticker}/{interval}: {e}",
        )
