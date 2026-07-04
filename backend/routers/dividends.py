# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /dividends — panel spółek dywidendowych (GPW).

Analizuje kuratorowaną listę polskich spółek dywidendowych, licząc
dedykowany score dywidendowy Z HISTORII WYPŁAT (nie z zawodnego .info).

Zwraca ranking posortowany po score dywidendowym, z podziałem na:
  - spółki płacące (z pełnym profilem)
  - spółki niewypłacające (osobno, jako informacja — nie błąd)

Score i logika: patrz dividends.py (moduł w root repo).
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

import dividends as div_engine
from tickers import SPOLKI_DYWIDENDOWE_GPW
from backend.core.security import OptionalCurrentUser

log = logging.getLogger("stockflow.dividends_router")

dividends_router = APIRouter(prefix="/dividends", tags=["dividends"])

# Cache wyników w pamięci: (timestamp, payload). TTL 15 min.
_cache: tuple[float, dict] | None = None
_CACHE_TTL_S = 15 * 60

# Czytelne nazwy spółek (fallback gdy yfinance nie zwróci longName)
_NAZWY = {
    "PKO.WA": "PKO BP", "PZU.WA": "PZU", "PEO.WA": "Bank Pekao",
    "PKN.WA": "Orlen", "KGH.WA": "KGHM", "SPL.WA": "Santander BP",
    "KTY.WA": "Grupa Kęty", "ACP.WA": "Asseco Poland", "LPP.WA": "LPP",
    "WPL.WA": "Wirtualna Polska", "OPL.WA": "Orange Polska", "PGE.WA": "PGE",
    "MBK.WA": "mBank", "BHW.WA": "Bank Handlowy", "ALR.WA": "Alior Bank",
    "KRU.WA": "Kruk", "GPW.WA": "GPW", "ATT.WA": "Grupa Azoty",
    "TPE.WA": "Tauron", "ENA.WA": "Enea", "CPS.WA": "Cyfrowy Polsat",
    "ASE.WA": "Asseco SEE", "NEU.WA": "Neuca", "BDX.WA": "Budimex",
}


def _analyze_one(ticker: str) -> dict | None:
    """Pobiera dane z yfinance i liczy profil dywidendowy jednej spółki."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        # Historia wypłat — niezawodne źródło (endpoint chart)
        dividends = t.dividends

        # Cena bieżąca — do wyliczenia stopy. Próbujemy z fast_info (szybkie),
        # potem z historii jako fallback.
        current_price = None
        try:
            fi = t.fast_info
            current_price = fi.get("lastPrice") or fi.get("last_price")
        except Exception:
            pass
        if not current_price:
            try:
                hist = t.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])
            except Exception:
                pass

        # Payout ratio z .info — traktowane jako korekta, nie fundament
        # (bywa zawodne, więc łapiemy błąd i idziemy dalej bez niego)
        payout = None
        try:
            info = t.info or {}
            payout = info.get("payoutRatio")
        except Exception:
            pass

        profil = div_engine.analyze_dividend(
            ticker, dividends, current_price, currency="PLN"
        )
        profil = div_engine.zastosuj_payout(profil, payout)

        # Dodaj czytelną nazwę
        profil["nazwa"] = _NAZWY.get(ticker, ticker.replace(".WA", ""))
        profil["cena"] = round(current_price, 2) if current_price else None

        # Usuń pole techniczne z odpowiedzi (wewnętrzne filary zostają, przydają się w UI)
        return profil

    except Exception as e:
        log.warning("Dividends: błąd analizy %s: %s", ticker, e)
        return None


@dividends_router.get(
    "",
    summary="Dividend stocks ranking",
    description="Ranking spółek dywidendowych GPW ze score liczonym z historii wypłat.",
)
def get_dividends(_user: OptionalCurrentUser = None) -> dict:
    # Cache 15 min — analiza 24 spółek przez yfinance przy każdym wejściu
    # grozi blokadą 429 i wolnym ładowaniem. Wyniki nie zmieniają się co minutę.
    global _cache
    now = time.time()
    if _cache and (now - _cache[0]) < _CACHE_TTL_S:
        return _cache[1]

    placace = []
    niewyplacajace = []
    bledy = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_analyze_one, t): t
            for t in SPOLKI_DYWIDENDOWE_GPW
        }
        for future in as_completed(futures):
            r = future.result()
            if r is None:
                bledy += 1
                continue
            if r["status"] == "OK":
                placace.append(r)
            elif r["status"] == "NIE_PLACI":
                niewyplacajace.append({
                    "ticker": r["ticker"], "nazwa": r["nazwa"],
                    "opis": r["opis"],
                })

    # Ranking: najwyższy score dywidendowy na górze
    placace.sort(key=lambda x: x["score"], reverse=True)

    # Statystyki zbiorcze dla nagłówka panelu
    srednia_stopa = None
    stopy = [p["yield_brutto"] for p in placace if p["yield_brutto"] is not None]
    if stopy:
        srednia_stopa = round(sum(stopy) / len(stopy), 2)

    payload = {
        "placace": placace,
        "niewyplacajace": niewyplacajace,
        "statystyki": {
            "liczba_placacych": len(placace),
            "liczba_niewyplacajacych": len(niewyplacajace),
            "srednia_stopa_brutto": srednia_stopa,
            "podatek_belki_pct": 19,
        },
    }
    # Zapisz do cache tylko sensowny wynik (nie pusty po awarii yfinance)
    if placace or niewyplacajace:
        _cache = (time.time(), payload)
    return payload
