"""
Portfolio Tracker
===================
Pozwala wpisać rzeczywiste pozycje (ile akcji, po jakiej cenie kupione)
i pokazuje:
- aktualną wartość portfela i zysk/stratę (P&L) na każdej pozycji i razem
- alokację sektorową (czy portfel jest zdywersyfikowany)
- średni "score" portfela (ważony wartością pozycji)
- ostrzeżenia o koncentracji (jedna spółka/sektor = zbyt duża część portfela)

To narzędzie analityczne - NIE zarządza prawdziwymi środkami, tylko
pomaga zrozumieć strukturę portfela na podstawie danych, które wpiszesz.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

import database as db
from stock_analyzer import fetch_history


CONCENTRATION_WARNING_POSITION = 0.30  # > 30% portfela w jednej spółce
CONCENTRATION_WARNING_SECTOR = 0.50    # > 50% portfela w jednym sektorze
HIGH_CORRELATION_THRESHOLD = 0.75      # od tego poziomu uznajemy korelację za "wysoką"


def analyze_portfolio(user_id: str, analyze_fn) -> dict:
    """
    Pobiera pozycje użytkownika z bazy, dolicza aktualne ceny i score
    (przez analyze_fn = stock_analyzer.analyze_ticker), i liczy podsumowanie.

    Zwraca dict z:
    - positions: lista pozycji z aktualną wartością, P&L, score, sektorem
    - totals: total_cost, total_value, total_pnl, total_pnl_pct, weighted_score
    - allocation_by_sector: {sektor: udział_procentowy}
    - warnings: lista ostrzeżeń o koncentracji
    - errors: tickery, dla których nie udało się pobrać danych
    """
    raw_positions = db.get_portfolio(user_id)
    if not raw_positions:
        return {
            "positions": [], "totals": None, "allocation_by_sector": {},
            "warnings": [], "errors": [],
        }

    positions = []
    errors = []

    for pos in raw_positions:
        ticker = pos["ticker"]
        try:
            res = analyze_fn(ticker)
        except Exception:
            errors.append(ticker)
            continue

        if "error" in res:
            errors.append(ticker)
            continue

        current_price = res["price"]
        shares = pos["shares"]
        cost_basis = shares * pos["buy_price"]
        current_value = shares * current_price
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0

        positions.append({
            "id": pos["id"],
            "ticker": ticker,
            "name": res["name"],
            "sector": res.get("sector", "Nieznany"),
            "shares": shares,
            "buy_price": pos["buy_price"],
            "buy_date": pos["buy_date"],
            "current_price": current_price,
            "currency": res["currency"],
            "cost_basis": round(cost_basis, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "score": res["total_score"],
            "notes": pos.get("notes", ""),
        })

    if not positions:
        return {
            "positions": [], "totals": None, "allocation_by_sector": {},
            "warnings": [], "errors": errors,
        }

    total_cost = sum(p["cost_basis"] for p in positions)
    total_value = sum(p["current_value"] for p in positions)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0

    weighted_score = (
        sum(p["score"] * p["current_value"] for p in positions) / total_value
        if total_value else 0.0
    )

    sector_values: dict = {}
    for p in positions:
        sector_values[p["sector"]] = sector_values.get(p["sector"], 0.0) + p["current_value"]
    allocation_by_sector = {
        sector: round(value / total_value * 100, 1)
        for sector, value in sorted(sector_values.items(), key=lambda x: -x[1])
    } if total_value else {}

    warnings = []
    for p in positions:
        share = p["current_value"] / total_value if total_value else 0
        if share > CONCENTRATION_WARNING_POSITION:
            warnings.append(
                f"⚠️ {p['ticker']} stanowi {share:.0%} portfela - "
                f"jedna spółka ma duży wpływ na cały wynik."
            )
    for sector, pct in allocation_by_sector.items():
        if pct / 100 > CONCENTRATION_WARNING_SECTOR:
            warnings.append(
                f"⚠️ Sektor '{sector}' stanowi {pct:.0f}% portfela - "
                f"słaba dywersyfikacja branżowa."
            )
    if len(positions) == 1:
        warnings.append(
            "⚠️ Portfel składa się z jednej spółki - brak dywersyfikacji."
        )

    return {
        "positions": positions,
        "totals": {
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "weighted_score": round(weighted_score, 1),
        },
        "allocation_by_sector": allocation_by_sector,
        "warnings": warnings,
        "errors": errors,
    }


def compute_correlation_matrix(tickers: list[str], period: str = "6mo") -> dict:
    """
    Liczy korelację dziennych zwrotów (% zmiany ceny) między podanymi
    tickerami. Wysoka korelacja (bliska 1) oznacza, że ceny ruszają się
    razem - czyli mimo różnych "etykietek" sektorowych, te pozycje mogą
    NIE dywersyfikować portfela tak, jak by się mogło wydawać.

    Zwraca:
    - matrix: pd.DataFrame (korelacje, NaN gdzie brak danych)
    - high_pairs: lista par (ticker1, ticker2, korelacja) >= HIGH_CORRELATION_THRESHOLD
    - errors: tickery, dla których nie udało się pobrać danych
    """
    returns = {}
    errors = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = fetch_history(stock, period=period)
            if df is None or df.empty or "Close" not in df:
                errors.append(ticker)
                continue
            returns[ticker] = df["Close"].pct_change().dropna()
        except Exception:
            errors.append(ticker)

    if len(returns) < 2:
        return {"matrix": None, "high_pairs": [], "errors": errors}

    returns_df = pd.DataFrame(returns).dropna(how="all")
    matrix = returns_df.corr()

    high_pairs = []
    cols = list(matrix.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            corr = matrix.loc[a, b]
            if pd.notna(corr) and corr >= HIGH_CORRELATION_THRESHOLD:
                high_pairs.append((a, b, round(float(corr), 2)))

    high_pairs.sort(key=lambda x: -x[2])

    return {"matrix": matrix, "high_pairs": high_pairs, "errors": errors}
