# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /forecast
  GET /forecast/{ticker}  — scenariusze cenowe (Monte Carlo + trend liniowy)

Udostępnia logikę z forecasting.py przez API dla frontendu Next.js.
"""

from __future__ import annotations

import os
import sys

from fastapi import APIRouter, HTTPException, Query

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.core.security import OptionalCurrentUser

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get(
    "/{ticker}",
    summary="Price scenarios (Monte Carlo + trend)",
)
async def get_forecast(
    ticker:  str,
    horizon: int = Query(30, ge=5, le=180, description="Horyzont w dniach"),
    _user:   OptionalCurrentUser = None,
) -> dict:
    """
    Zwraca scenariusze cenowe:
    - Monte Carlo (GBM) z percentylami 5/25/50/75/95
    - Trend liniowy z przedziałem ufności 90%
    - Statystyki i interpretacja
    """
    ticker = ticker.strip().upper()

    # Pobierz dane historyczne przez istniejący moduł
    try:
        import yfinance as yf
        import stock_analyzer
        df = stock_analyzer.fetch_history(yf.Ticker(ticker), period="1y")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Nie udało się pobrać danych: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Brak danych dla {ticker}")

    try:
        import forecasting

        mc    = forecasting.monte_carlo_forecast(df, horizon_days=horizon)
        trend = forecasting.linear_trend_forecast(df, horizon_days=horizon)

        if "error" in mc:
            raise HTTPException(status_code=422, detail=mc["error"])

        # Konwertuj daty na stringi (JSON-safe)
        mc_dates = [d.strftime("%Y-%m-%d") for d in mc["dates"]]
        trend_dates = (
            [d.strftime("%Y-%m-%d") for d in trend["dates"]]
            if "error" not in trend else []
        )

        interpretation = forecasting.interpret_forecast(mc["stats"])

        return {
            "ticker":  ticker,
            "horizon": horizon,
            "monte_carlo": {
                "dates":       mc_dates,
                "percentiles": mc["percentiles"],   # {5,25,50,75,95}: [...]
                "stats":       mc["stats"],
            },
            "trend": (
                {
                    "dates":    trend_dates,
                    "forecast": trend["forecast"],
                    "lower_90": trend["lower_90"],
                    "upper_90": trend["upper_90"],
                    "slope_pct_per_day": trend["slope_pct_per_day"],
                }
                if "error" not in trend else None
            ),
            "interpretation": interpretation,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd prognozowania: {e}")


# ── News endpoint ──────────────────────────────────────────────────────

news_router = APIRouter(prefix="/news", tags=["news"])


@news_router.get(
    "/{ticker}",
    summary="Latest news for instrument",
)
async def get_news(
    ticker: str,
    limit:  int = Query(8, ge=1, le=20),
    _user:  OptionalCurrentUser = None,
) -> dict:
    """Zwraca najnowsze newsy dla instrumentu z yfinance."""
    ticker = ticker.strip().upper()
    try:
        import yfinance as yf
        import stock_analyzer
        stock = yf.Ticker(ticker)
        raw   = stock_analyzer.fetch_news(stock)
        items = stock_analyzer.get_news_list(raw, limit=limit)
        return {"ticker": ticker, "news": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Nie udało się pobrać newsów: {e}")
