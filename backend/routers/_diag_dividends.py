# ⚠️ TYMCZASOWY PLIK DIAGNOSTYCZNY — USUŃ PO UŻYCIU ⚠️
#
# Cel: sprawdzić z adresu IP Railway (produkcja), czy yfinance zwraca
# dane dywidendowe dla GPW. Lokalny test zawiódł (429 / słaby hotspot),
# więc testujemy z tego samego środowiska, w którym docelowo działałby
# panel dywidendowy.
#
# UŻYCIE:
# 1. Wgraj ten plik jako backend/routers/_diag_dividends.py
# 2. Zarejestruj w main.py (patrz instrukcja na dole tego pliku)
# 3. Otwórz w przeglądarce: https://<twoj-backend>/api/v1/_diag/dividends
# 4. Przeczytaj wynik (JSON)
# 5. USUŃ ten plik i wpis w main.py, zrób redeploy
#
# Endpoint NIE wymaga logowania (celowo, dla szybkiego testu przez przeglądarkę)
# i NIE zapisuje niczego do bazy — czysto odczytowy, bezpieczny do jednorazowego użycia.

from __future__ import annotations

import time
import random
import logging
from fastapi import APIRouter

log = logging.getLogger("stockflow.diag")

router = APIRouter(prefix="/_diag", tags=["_diagnostics_temp"])

# Ta sama próbka co w lokalnej sondzie — duże + średnie spółki GPW
SPOLKI = [
    ("PKO.WA", "PKO BP"), ("PZU.WA", "PZU"), ("PKN.WA", "Orlen"),
    ("KGH.WA", "KGHM"), ("PEO.WA", "Pekao"), ("SPL.WA", "Santander PL"),
    ("LPP.WA", "LPP"), ("DNP.WA", "Dino"),
    ("ATT.WA", "Grupa Azoty"), ("KTY.WA", "Kęty"),
    ("ACP.WA", "Asseco Poland"), ("WPL.WA", "Wirtualna Polska"),
]

DELAY_S = 1.5   # Railway ma lepsze łącze niż domowy hotspot — krótsza przerwa wystarczy
MAX_RETRIES = 2
RETRY_BACKOFF_S = 8


def _check_one(ticker: str) -> dict:
    import yfinance as yf

    wynik = {
        "ticker": ticker,
        "dividends": {"dziala": False, "lata": 0, "wyplat": 0, "ostatnia": None, "blad": None},
        "info":      {"dziala": False, "yield": None, "payout": None, "blad": None},
    }

    t = yf.Ticker(ticker)

    # Test .dividends (endpoint chart — kluczowy, rdzeń score dywidendowego)
    for probe in range(1, MAX_RETRIES + 1):
        try:
            divs = t.dividends
            if divs is not None and not divs.empty:
                wynik["dividends"]["wyplat"]   = int(len(divs))
                wynik["dividends"]["lata"]     = int(len(divs.index.year.unique()))
                wynik["dividends"]["ostatnia"] = str(divs.index[-1].date())
            wynik["dividends"]["dziala"] = True
            break
        except Exception as e:
            err = str(e)
            if ("429" in err or "Too Many Requests" in err) and probe < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_S)
                continue
            wynik["dividends"]["blad"] = err[:120]
            break

    time.sleep(1.0)

    # Test .info (endpoint quoteSummary — znany bug z "crumb", niezależny od GPW)
    for probe in range(1, MAX_RETRIES + 1):
        try:
            info = t.info or {}
            wynik["info"]["yield"]  = info.get("dividendYield")
            wynik["info"]["payout"] = info.get("payoutRatio")
            wynik["info"]["dziala"] = True
            break
        except Exception as e:
            err = str(e)
            if ("429" in err or "Too Many Requests" in err) and probe < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_S)
                continue
            wynik["info"]["blad"] = err[:120]
            break

    return wynik


@router.get(
    "/dividends",
    summary="[TYMCZASOWE] Test dostępności danych dywidendowych GPW",
    description="Diagnostyka jednorazowa — usuń po użyciu. Testuje yfinance z IP Railway.",
)
async def diag_dividends() -> dict:
    results = []
    for i, (ticker, nazwa) in enumerate(SPOLKI):
        w = _check_one(ticker)
        w["nazwa"] = nazwa
        results.append(w)
        if i < len(SPOLKI) - 1:
            time.sleep(random.uniform(DELAY_S, DELAY_S + 1))

    hist_ok = sum(1 for r in results if r["dividends"]["dziala"] and r["dividends"]["lata"] >= 3)
    info_ok = sum(1 for r in results if r["info"]["dziala"] and (r["info"]["yield"] or r["info"]["payout"]))
    total = len(SPOLKI)

    if hist_ok >= total * 0.7:
        werdykt = "WYKONALNE — większość spółek ma sensowną historię dywidend (3+ lata)."
    elif hist_ok >= total * 0.4:
        werdykt = "CZĘŚCIOWO WYKONALNE — rozważ ograniczenie panelu do spółek z potwierdzoną historią."
    else:
        werdykt = "RYZYKOWNE — za mało spółek ma dostępną historię, potrzebne inne źródło danych."

    return {
        "podsumowanie": {
            "spolek_testowanych": total,
            "historia_dywidend_ok": f"{hist_ok}/{total}",
            "info_yield_payout_ok": f"{info_ok}/{total}",
            "werdykt": werdykt,
        },
        "szczegoly": results,
        "uwaga": (
            "'info' (yield/payout) może zawodzić niezależnie od 'dividends' — "
            "to osobny, znany problem yfinance (token 'crumb'), nie brak danych GPW. "
            "Liczy się głównie 'dividends' jako rdzeń przyszłego score dywidendowego."
        ),
    }
