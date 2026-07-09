# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /calendar — kalendarz rynkowy dla watchlisty użytkownika.

Agreguje nadchodzące wydarzenia (wyniki finansowe, dni ex-dividend)
dla wszystkich spółek z watchlisty w jeden chronologiczny widok —
"co się dzieje w tym tygodniu z moimi spółkami".

Kalendarz per-ticker jest cache'owany 6h w pamięci procesu — daty
wyników/ex-dividend zmieniają się rzadko, a każde pobranie to osobne
zapytanie do yfinance (ryzyko 429 przy dużych watchlistach).
"""

from __future__ import annotations

import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from stock_analyzer import get_calendar_info
from backend.core.security import CurrentUser

log = logging.getLogger("stockflow.calendar")

calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])

# Cache: {ticker: (timestamp, calendar_dict)}
_cal_cache: dict[str, tuple[float, dict]] = {}
_CAL_TTL_S = 6 * 3600


def _calendar_for(ticker: str) -> dict:
    now = time.time()
    cached = _cal_cache.get(ticker)
    if cached and (now - cached[0]) < _CAL_TTL_S:
        return cached[1]
    try:
        import yfinance as yf
        cal = get_calendar_info(yf.Ticker(ticker)) or {}
    except Exception as e:
        log.warning("Calendar: błąd dla %s: %s", ticker, e)
        cal = {}
    _cal_cache[ticker] = (now, cal)
    return cal


@calendar_router.get(
    "",
    summary="Market calendar for user's watchlist",
    description="Nadchodzące wyniki finansowe i dni ex-dividend dla spółek z watchlisty, posortowane chronologicznie.",
)
def get_calendar(user_id: CurrentUser) -> dict:
    watchlist = db.get_watchlist(user_id)
    tickers = [w["ticker"] for w in watchlist]

    if not tickers:
        return {"events": [], "tickers_checked": 0}

    events: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_calendar_for, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            cal = future.result()
            if cal.get("earnings_date"):
                events.append({
                    "ticker": ticker,
                    "type":   "earnings",
                    "label":  "Wyniki finansowe",
                    "date":   str(cal["earnings_date"]),
                })
            if cal.get("ex_dividend_date"):
                events.append({
                    "ticker": ticker,
                    "type":   "ex_dividend",
                    "label":  "Ex-dividend",
                    "date":   str(cal["ex_dividend_date"]),
                })

    # Chronologicznie, najbliższe najpierw (daty ISO sortują się leksykalnie)
    events.sort(key=lambda e: e["date"])

    return {"events": events, "tickers_checked": len(tickers)}
