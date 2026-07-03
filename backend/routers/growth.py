# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /growth — spółki wzrostowe.

To NIE prywatne startupy (dane przed-IPO nie są publiczne). To spółki
już notowane, często po niedawnym IPO lub w fazie szybkiego wzrostu —
ciekawe do śledzenia, ale zwykle bardziej zmienne i ryzykowne.

Wykorzystuje ten sam silnik analizy co skaner (analyze_ticker),
uruchamiany równolegle (ThreadPoolExecutor).
"""

from __future__ import annotations

import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from stock_analyzer import analyze_ticker
from tickers import SPOLKI_WZROSTOWE
from backend.core.security import OptionalCurrentUser

log = logging.getLogger("stockflow.growth")

growth_router = APIRouter(prefix="/growth", tags=["growth"])

# Kategoria wywnioskowana z pozycji na liście (na podstawie komentarzy grup).
# Prosto: mapujemy ticker -> kategoria dla ładnego grupowania w UI.
_CATEGORIES = {
    "ARM": "AI / Chipy", "ALAB": "AI / Chipy", "PLTR": "AI / Chipy",
    "SMCI": "AI / Chipy", "MRVL": "AI / Chipy",
    "CRWD": "Cyberbezpieczeństwo", "ZS": "Cyberbezpieczeństwo",
    "SNOW": "Chmura / SaaS", "DDOG": "Chmura / SaaS", "NET": "Chmura / SaaS",
    "KVYO": "Chmura / SaaS",
    "RDDT": "Fintech / Internet", "AFRM": "Fintech / Internet",
    "XYZ": "Fintech / Internet", "SHOP": "Fintech / Internet",
    "ALE.WA": "Polskie (GPW)", "PCO.WA": "Polskie (GPW)", "TXT.WA": "Polskie (GPW)",
    "XTB.WA": "Polskie (GPW)", "DNP.WA": "Polskie (GPW)",
}


def _analyze_one(name: str, ticker: str, opis: str) -> dict | None:
    try:
        res = analyze_ticker(ticker)
        if "error" in res or res.get("price") is None or res["price"] <= 0:
            return None
        return {
            "ticker":      ticker,
            "name":        res.get("name", name),
            "display_name": name,
            "description": opis,
            "category":    _CATEGORIES.get(ticker, "Inne"),
            "price":       res["price"],
            "currency":    res.get("currency", "USD"),
            "score":       res.get("total_score", 50.0),
            "score_st":    res.get("score_st"),
            "sector":      res.get("sector", "Nieznany"),
        }
    except Exception as e:
        log.warning("Growth: błąd analizy %s: %s", ticker, e)
        return None


@growth_router.get(
    "",
    summary="Growth stocks",
    description="Analiza spółek wzrostowych — score, cena, kategoria. Posortowane malejąco wg score.",
)
async def get_growth(_user: OptionalCurrentUser = None) -> dict:
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_analyze_one, name, tckr, opis): tckr
            for name, (tckr, opis) in SPOLKI_WZROSTOWE.items()
        }
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)

    # Zbierz też listę kategorii (do filtrów w UI)
    categories = sorted({r["category"] for r in results})

    return {
        "stocks":     results,
        "categories": categories,
        "count":      len(results),
    }
