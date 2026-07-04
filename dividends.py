# Copyright (c) 2026 Damian Migała / StockFlow

"""
Score dywidendowy — dla panelu "Dywidendy".

Kluczowa decyzja projektowa (potwierdzona sondą danych GPW):
liczymy WSZYSTKO Z HISTORII WYPŁAT (stock.dividends), która jest
niezawodna, a NIE z pola .info['dividendYield'] — bo .info bywa
niespójne i czasem błędne (np. KGHM pokazywał 0.45% i payout 0%).

Trzy filary score (0-100):
  1. Bezpieczeństwo (40%) — czy dywidenda się utrzyma (payout ratio)
  2. Ciągłość i wzrost (35%) — regularność i trend wypłat z historii
  3. Atrakcyjność (25%) — stopa dywidendy wyliczona z historii + ceny

Przypadki brzegowe (znalezione w sondzie):
  - Spółka nie płaci dywidend (np. Dino) -> status "NIE_PLACI", nie błąd
  - Payout > 100% (np. Orlen) -> flaga ostrzegawcza, obniżony score
  - Brak/niepełne dane -> status "BRAK_DANYCH", pomijana w rankingu

Polski kontekst: obliczamy też stopę NETTO po podatku Belki (19%).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger("stockflow.dividends")

PODATEK_BELKI = 0.19   # 19% podatek od zysków kapitałowych (dywidend) w PL


def _roczne_dywidendy(dividends) -> dict[int, float]:
    """Grupuje serię wypłat (pandas Series z DatetimeIndex) na sumy roczne.
    Zwraca {rok: suma_wyplat_w_roku}."""
    roczne: dict[int, float] = {}
    for data, kwota in dividends.items():
        rok = data.year
        roczne[rok] = roczne.get(rok, 0.0) + float(kwota)
    return roczne


def analyze_dividend(ticker: str, dividends, current_price: float | None,
                     currency: str = "PLN") -> dict:
    """
    Główna funkcja: analizuje profil dywidendowy spółki z historii wypłat.

    Argumenty:
      ticker         — symbol (do logów)
      dividends      — pandas Series wypłat (z yfinance stock.dividends)
      current_price  — aktualna cena (do wyliczenia stopy); może być None
      currency       — waluta instrumentu

    Zwraca dict ze statusem, score i szczegółami. Status:
      "OK"          — pełny profil dywidendowy
      "NIE_PLACI"   — spółka nie wypłaca dywidend (nie błąd!)
      "BRAK_DANYCH" — za mało danych do oceny
    """
    # Brak historii = spółka nie płaci albo brak danych
    if dividends is None or len(dividends) == 0:
        return {
            "ticker": ticker, "status": "NIE_PLACI",
            "score": None, "yield_brutto": None, "yield_netto": None,
            "lata_ciaglosci": 0, "ostatnia_wyplata": None,
            "payout_ratio": None, "flagi": [],
            "opis": "Spółka nie wypłaca dywidendy",
        }

    roczne = _roczne_dywidendy(dividends)
    biezacy_rok = datetime.now(timezone.utc).year

    # Dywidenda z ostatnich 12 miesięcy (do wyliczenia stopy)
    # Bierzemy sumę z ostatniego pełnego roku wypłat.
    lata_z_wyplatami = sorted([r for r in roczne if roczne[r] > 0], reverse=True)
    if not lata_z_wyplatami:
        return {
            "ticker": ticker, "status": "NIE_PLACI",
            "score": None, "yield_brutto": None, "yield_netto": None,
            "lata_ciaglosci": 0, "ostatnia_wyplata": None,
            "payout_ratio": None, "flagi": [],
            "opis": "Spółka nie wypłaca dywidendy",
        }

    # Ostatnia znacząca dywidenda roczna (pomijamy bieżący rok jeśli niepełny)
    ostatni_pelny_rok = lata_z_wyplatami[0]
    if ostatni_pelny_rok == biezacy_rok and len(lata_z_wyplatami) > 1:
        # bieżący rok może być niepełny — użyj do stopy, ale porównuj z poprzednim
        dywidenda_roczna = roczne[ostatni_pelny_rok]
    else:
        dywidenda_roczna = roczne[ostatni_pelny_rok]

    ostatnia_data = str(dividends.index[-1].date())

    flagi: list[str] = []

    # ── FILAR 1: Bezpieczeństwo (0-100, waga 40%) ──
    # Bazujemy na payout ratio jeśli dostępny (z info, przekazany osobno),
    # ale głównie oceniamy przez pryzmat stabilności wypłat.
    # Tu payout przyjdzie z zewnątrz (info) — ale nie ufamy mu bezkrytycznie.
    bezpieczenstwo = 60.0  # bazowa wartość neutralna

    # ── FILAR 2: Ciągłość i wzrost (0-100, waga 35%) ──
    lata_ciaglosci = _policz_ciaglosc(roczne, biezacy_rok)
    ciaglosc_score = min(100, 40 + lata_ciaglosci * 6)  # 10 lat -> 100

    # Trend wzrostowy: porównaj średnią z ostatnich 3 lat do wcześniejszych 3
    trend = _ocen_trend(roczne, biezacy_rok)
    if trend == "rosnacy":
        ciaglosc_score = min(100, ciaglosc_score + 10)
        flagi.append(("pozytyw", "Rosnąca dywidenda"))
    elif trend == "malejacy":
        ciaglosc_score = max(0, ciaglosc_score - 15)
        flagi.append(("ostrzezenie", "Malejąca dywidenda"))

    if lata_ciaglosci >= 10:
        flagi.append(("pozytyw", f"{lata_ciaglosci} lat nieprzerwanych wypłat"))

    # ── FILAR 3: Atrakcyjność (0-100, waga 25%) ──
    yield_brutto = None
    yield_netto = None
    atrakcyjnosc = 50.0
    if current_price and current_price > 0:
        yield_brutto = round(dywidenda_roczna / current_price * 100, 2)
        yield_netto = round(yield_brutto * (1 - PODATEK_BELKI), 2)

        if 3 <= yield_brutto <= 7:
            atrakcyjnosc = 85  # słodki punkt — atrakcyjna ale zdrowa
        elif 1 <= yield_brutto < 3:
            atrakcyjnosc = 60  # niska ale bezpieczna
        elif 7 < yield_brutto <= 10:
            atrakcyjnosc = 65
            flagi.append(("ostrzezenie", "Bardzo wysoka stopa — sprawdź trwałość"))
        elif yield_brutto > 10:
            atrakcyjnosc = 40
            flagi.append(("ostrzezenie", "Ekstremalnie wysoka stopa — ryzyko cięcia"))
        else:
            atrakcyjnosc = 45

    # ── Score końcowy ──
    score = round(
        bezpieczenstwo * 0.40 +
        ciaglosc_score * 0.35 +
        atrakcyjnosc   * 0.25,
        1
    )

    return {
        "ticker": ticker,
        "status": "OK",
        "score": score,
        "yield_brutto": yield_brutto,
        "yield_netto": yield_netto,
        "lata_ciaglosci": lata_ciaglosci,
        "ostatnia_wyplata": ostatnia_data,
        "dywidenda_roczna": round(dywidenda_roczna, 2),
        "trend": trend,
        "payout_ratio": None,   # uzupełniane z info na poziomie routera
        "flagi": flagi,
        "opis": _opis_slowny(score, lata_ciaglosci, trend),
        "_filary": {
            "bezpieczenstwo": round(bezpieczenstwo, 0),
            "ciaglosc": round(ciaglosc_score, 0),
            "atrakcyjnosc": round(atrakcyjnosc, 0),
        },
    }


def zastosuj_payout(profil: dict, payout_ratio: float | None) -> dict:
    """Nakłada payout ratio (z info) na profil — koryguje filar bezpieczeństwa.
    Wywoływane osobno, bo payout pochodzi z .info które bywa zawodne,
    więc traktujemy je jako korektę, nie fundament."""
    if profil["status"] != "OK" or payout_ratio is None:
        return profil

    profil["payout_ratio"] = round(payout_ratio, 3)
    bezp = profil["_filary"]["bezpieczenstwo"]

    if payout_ratio > 1.0:
        bezp = 25
        profil["flagi"].insert(0, ("ostrzezenie", "Dywidenda niepokryta zyskiem (payout >100%)"))
    elif payout_ratio > 0.8:
        bezp = 55
        profil["flagi"].append(("neutralny", "Wysoki payout ratio"))
    elif payout_ratio > 0.4:
        bezp = 80
        profil["flagi"].append(("pozytyw", "Zdrowy payout ratio"))
    elif payout_ratio > 0:
        bezp = 70

    profil["_filary"]["bezpieczenstwo"] = bezp
    # Przelicz score z nowym bezpieczeństwem
    profil["score"] = round(
        bezp * 0.40 +
        profil["_filary"]["ciaglosc"] * 0.35 +
        profil["_filary"]["atrakcyjnosc"] * 0.25,
        1
    )
    return profil


def _policz_ciaglosc(roczne: dict[int, float], biezacy_rok: int) -> int:
    """Liczy ile lat WSTECZ bez przerwy spółka płaciła dywidendę.
    Pomija bieżący rok jeśli jeszcze nie było wypłaty (może być za wcześnie)."""
    lata = 0
    rok = biezacy_rok
    # jeśli w tym roku jeszcze nie zapłacono, zacznij od poprzedniego
    if roczne.get(rok, 0) == 0:
        rok -= 1
    while roczne.get(rok, 0) > 0:
        lata += 1
        rok -= 1
    return lata


def _ocen_trend(roczne: dict[int, float], biezacy_rok: int) -> str:
    """Porównuje średnią wypłat z ostatnich ~3 lat do wcześniejszych ~3.
    Zwraca 'rosnacy' / 'malejacy' / 'stabilny'."""
    lata = sorted([r for r in roczne if roczne[r] > 0], reverse=True)
    if len(lata) < 4:
        return "stabilny"  # za mało danych na ocenę trendu
    ostatnie = lata[:3]
    wczesniejsze = lata[3:6]
    if not wczesniejsze:
        return "stabilny"
    sr_ostatnie = sum(roczne[r] for r in ostatnie) / len(ostatnie)
    sr_wczesniej = sum(roczne[r] for r in wczesniejsze) / len(wczesniejsze)
    if sr_wczesniej == 0:
        return "stabilny"
    zmiana = (sr_ostatnie - sr_wczesniej) / sr_wczesniej
    if zmiana > 0.10:
        return "rosnacy"
    if zmiana < -0.10:
        return "malejacy"
    return "stabilny"


def _opis_slowny(score: float, lata: int, trend: str) -> str:
    """Krótki, ludzki opis profilu dywidendowego."""
    if score >= 75:
        baza = "Solidny profil dywidendowy"
    elif score >= 55:
        baza = "Przyzwoity profil dywidendowy"
    else:
        baza = "Profil dywidendowy z zastrzeżeniami"

    dodatki = []
    if lata >= 10:
        dodatki.append("długa historia wypłat")
    if trend == "rosnacy":
        dodatki.append("dywidenda rośnie")
    elif trend == "malejacy":
        dodatki.append("dywidenda maleje")

    if dodatki:
        return f"{baza} — {', '.join(dodatki)}"
    return baza
