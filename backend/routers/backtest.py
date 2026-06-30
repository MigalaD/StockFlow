# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /backtest
  GET /backtest/{ticker}            — pełny backtest strategii score
  GET /backtest/{ticker}/grid       — heatmapa progów (buy × sell)
  GET /backtest/{ticker}/walkforward — analiza walk-forward (stabilność)

Udostępnia logikę z backtest.py przez API.
"""

from __future__ import annotations

import os
import sys

from fastapi import APIRouter, HTTPException, Query

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.core.security import OptionalCurrentUser

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get(
    "/{ticker}",
    summary="Backtest score strategy",
)
async def run_backtest(
    ticker:          str,
    period:          str   = Query("2y", description="Okres: 1y, 2y, 5y"),
    buy_threshold:   float = Query(65, ge=0, le=100),
    sell_threshold:  float = Query(35, ge=0, le=100),
    initial_capital: float = Query(10_000, gt=0),
    _user:           OptionalCurrentUser = None,
) -> dict:
    """
    Pełny backtest: kup gdy score ≥ buy, sprzedaj gdy score ≤ sell.
    Zwraca equity curve, transakcje i metryki ryzyka (Sharpe, Sortino, DD).
    """
    ticker = ticker.strip().upper()

    if buy_threshold <= sell_threshold:
        raise HTTPException(status_code=422, detail="buy_threshold musi być > sell_threshold")

    try:
        import backtest as bt
        result = bt.backtest_score_strategy(
            ticker, period=period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            initial_capital=initial_capital,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Błąd backtestu: {e}")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Konwertuj equity_curve DataFrame → lista dict (JSON-safe)
    eq = result["equity_curve"]
    equity_curve = [
        {
            "date":     d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
            "strategy": round(float(s), 2),
            "buyhold":  round(float(b), 2),
        }
        for d, s, b in zip(eq["Date"], eq["Strategy"], eq["BuyHold"])
    ]

    # Decymacja dla wydajności (max ~150 punktów)
    if len(equity_curve) > 150:
        step = len(equity_curve) // 150
        equity_curve = equity_curve[::step]

    # Transakcje — konwersja dat
    trades = []
    for t in result["trades"]:
        trades.append({
            "entry_date":  str(t["kupno"])[:10],
            "exit_date":   str(t["sprzedaz"])[:10],
            "entry_price": t["cena_kupna"],
            "exit_price":  t["cena_sprzedazy"],
            "return_pct":  t["zwrot_%"],
            "still_open":  "uwaga" in t,
        })

    return {
        "ticker":       ticker,
        "period":       period,
        "buy_threshold":  buy_threshold,
        "sell_threshold": sell_threshold,
        "equity_curve": equity_curve,
        "trades":       trades,
        "metrics":      result["metrics"],
    }


@router.get(
    "/{ticker}/grid",
    summary="Threshold grid heatmap",
)
async def threshold_grid(
    ticker: str,
    period: str = Query("2y"),
    _user:  OptionalCurrentUser = None,
) -> dict:
    """
    Testuje wiele kombinacji progów buy×sell i zwraca dane do heatmapy.
    Pomaga znaleźć optymalne progi (i sprawdzić czy nie ma overfittingu).
    """
    ticker = ticker.strip().upper()

    try:
        import backtest as bt
        result = bt.run_threshold_grid(ticker, period=period)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Błąd grid: {e}")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Grid DataFrame → lista komórek {buy, sell, return}
    grid = result["grid"]
    cells = []
    for sell in grid.index:
        for buy in grid.columns:
            val = grid.loc[sell, buy]
            if val == val:  # nie NaN
                cells.append({
                    "buy":    int(buy),
                    "sell":   int(sell),
                    "return": round(float(val), 1),
                })

    return {
        "ticker":         ticker,
        "cells":          cells,
        "best":           result["best"],
        "buyhold_return": result["buyhold_return"],
    }


@router.get(
    "/{ticker}/walkforward",
    summary="Walk-forward analysis",
)
async def walk_forward(
    ticker:         str,
    period:         str   = Query("5y"),
    buy_threshold:  float = Query(65, ge=0, le=100),
    sell_threshold: float = Query(35, ge=0, le=100),
    n_windows:      int   = Query(4, ge=2, le=8),
    _user:          OptionalCurrentUser = None,
) -> dict:
    """
    Dzieli historię na N nieprzykrywających się okien i testuje regułę
    w każdym osobno. Sprawdza czy strategia działa konsekwentnie,
    czy tylko w jednym szczególnym okresie.
    """
    ticker = ticker.strip().upper()

    try:
        import backtest as bt
        result = bt.walk_forward_analysis(
            ticker, period=period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            n_windows=n_windows,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Błąd walk-forward: {e}")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return {
        "ticker":  ticker,
        "windows": result["windows"],
        "summary": result["summary"],
    }
