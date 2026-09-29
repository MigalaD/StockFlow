# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /commodities — panel surowców.

Używamy ETF-ów towarowych (GLD, USO...) zamiast kontraktów futures (=F) —
płynne, stabilna historia w yfinance (decyzja udokumentowana w tickers.py).
Score dla surowców = czysta analiza techniczna (fundamenty spółek
z definicji nie istnieją — stock_analyzer wyklucza je automatycznie).

Wzorce z growth.py: cache 15 min, `def` (nie async — blokujące yfinance).
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
from tickers import KOMODITY_LIST
from tickers_i18n import describe
from backend.core.lang import RequestLang
from backend.core.security import OptionalCurrentUser

log = logging.getLogger("stockflow.commodities")

commodities_router = APIRouter(prefix="/commodities", tags=["commodities"])

# Cache kluczowany JĘZYKIEM: bez tego użytkownik EN dostałby polską
# treść z cache'a zapełnionego przez użytkownika PL (i odwrotnie).
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_S = 15 * 60

_CATEGORIES = {
    "GLD": "Metale szlachetne", "SLV": "Metale szlachetne",
    "PPLT": "Metale szlachetne", "PALL": "Metale szlachetne",
    "USO": "Energia", "UNG": "Energia",
    "CPER": "Przemysłowe",
    "DBA": "Rolnictwo", "WEAT": "Rolnictwo", "CORN": "Rolnictwo",
    "DBC": "Koszyki",
}


def _analyze_one(name: str, ticker: str, opis: str, lang: str = "pl") -> dict | None:
    try:
        res = analyze_ticker(ticker, lang)
        if "error" in res or res.get("price") is None or res["price"] <= 0:
            return None
        return {
            "ticker":       ticker,
            "name":         res.get("name", name),
            "display_name": name,
            "description":  describe(ticker, opis, lang),
            "category":     _CATEGORIES.get(ticker, "Inne"),
            "price":        res["price"],
            "currency":     res.get("currency", "USD"),
            "score":        res.get("total_score", 50.0),
            "score_st":     res.get("score_st"),
            "sector":       "Surowce",
        }
    except Exception as e:
        log.warning("Commodities: błąd analizy %s: %s", ticker, e)
        return None


@commodities_router.get(
    "",
    summary="Commodities panel",
    description="Analiza surowców (przez ETF-y towarowe) — złoto, srebro, ropa, gaz, metale, rolnictwo.",
)
def get_commodities(lang: RequestLang, _user: OptionalCurrentUser = None) -> dict:
    now = time.time()
    cached = _cache.get(lang)
    if cached and (now - cached[0]) < _CACHE_TTL_S:
        return cached[1]

    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_analyze_one, name, tckr, opis, lang): tckr
            for name, (tckr, opis) in KOMODITY_LIST.items()
        }
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)
    categories = sorted({r["category"] for r in results})

    payload = {"stocks": results, "categories": categories, "count": len(results)}
    if results:
        _cache[lang] = (now, payload)
    return payload
