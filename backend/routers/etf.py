# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /etf — panel ETF-ów.

Kluczowy polski akcent: oznaczenie UCITS. Polski inwestor detaliczny
zwykle NIE kupi amerykańskich ETF-ów (SPY/QQQ) przez regulacje PRIIPs
(brak dokumentu KID) — wersje UCITS notowane w Europie TAK. Panel
wyraźnie to rozróżnia, żeby użytkownik wiedział, co realnie kupi
u polskiego brokera.

Wzorce z growth.py: cache 15 min (ochrona przed 429), `def` nie
`async def` (blokujące yfinance w threadpoolu FastAPI, nie w event loop).
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

from stock_analyzer import analyze_ticker
from tickers import ETF_LIST
from backend.core.security import OptionalCurrentUser

log = logging.getLogger("stockflow.etf")

etf_router = APIRouter(prefix="/etf", tags=["etf"])

_cache: tuple[float, dict] | None = None
_CACHE_TTL_S = 15 * 60

# Kategorie do filtrów w UI. UCITS wydzielone jako osobna, najważniejsza
# kategoria dla polskiego użytkownika.
_CATEGORIES = {
    "VWCE.DE": "UCITS (dostępne w PL)", "SXR8.DE": "UCITS (dostępne w PL)",
    "IWDA.AS": "UCITS (dostępne w PL)", "EUNL.DE": "UCITS (dostępne w PL)",
    "VUSA.AS": "UCITS (dostępne w PL)",
    "SPY": "Szerokie indeksy USA", "QQQ": "Szerokie indeksy USA",
    "VTI": "Szerokie indeksy USA",
    "EFA": "Świat / Emerging", "VWO": "Świat / Emerging",
    "XLK": "Sektorowe", "XLE": "Sektorowe", "XLF": "Sektorowe",
    "ARKK": "Sektorowe",
    "VNQ": "Obligacje / REIT", "TLT": "Obligacje / REIT",
    "ETFW20L.WA": "GPW",
}

_UCITS = {"VWCE.DE", "SXR8.DE", "IWDA.AS", "EUNL.DE", "VUSA.AS", "ETFW20L.WA"}


def _analyze_one(name: str, ticker: str, opis: str) -> dict | None:
    try:
        res = analyze_ticker(ticker)
        if "error" in res or res.get("price") is None or res["price"] <= 0:
            return None
        return {
            "ticker":       ticker,
            "name":         res.get("name", name),
            "display_name": name,
            "description":  opis,
            "category":     _CATEGORIES.get(ticker, "Inne"),
            "ucits":        ticker in _UCITS,
            "price":        res["price"],
            "currency":     res.get("currency", "USD"),
            "score":        res.get("total_score", 50.0),
            "score_st":     res.get("score_st"),
            "sector":       "ETF",
        }
    except Exception as e:
        log.warning("ETF: błąd analizy %s: %s", ticker, e)
        return None


@etf_router.get(
    "",
    summary="ETF panel",
    description="Analiza popularnych ETF-ów (w tym UCITS dostępnych dla polskich inwestorów). Posortowane wg score.",
)
def get_etfs(_user: OptionalCurrentUser = None) -> dict:
    global _cache
    now = time.time()
    if _cache and (now - _cache[0]) < _CACHE_TTL_S:
        return _cache[1]

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_analyze_one, name, tckr, opis): tckr
            for name, (tckr, opis) in ETF_LIST.items()
        }
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)
    categories = sorted({r["category"] for r in results})

    payload = {"stocks": results, "categories": categories, "count": len(results)}
    if results:
        _cache = (now, payload)
    return payload
