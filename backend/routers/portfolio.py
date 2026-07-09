# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /portfolio — zarządzanie portfelem użytkownika.

WAŻNE: to jest router FastAPI (endpointy HTTP). Logika biznesowa
(liczenie P&L, konwersja walut, wagi sektorowe) mieszka w module
`portfolio.py` w głównym katalogu repo — ten plik go tylko woła
i opakowuje w odpowiedzi HTTP.
"""

from __future__ import annotations

import os
import sys

from fastapi import APIRouter, HTTPException, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
import portfolio as portfolio_logic
from stock_analyzer import analyze_ticker
from backend.core.security import CurrentUser
from backend.models.schemas import (
    PortfolioResponse,
    PositionItem,
    PositionAddRequest,
    PortfolioImportRequest,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get portfolio with P&L",
)
async def get_portfolio(user_id: CurrentUser) -> PortfolioResponse:
    result = portfolio_logic.analyze_portfolio(user_id, analyze_ticker)

    positions = [
        PositionItem(
            id            = p["id"],
            ticker        = p["ticker"],
            name          = p["name"],
            sector        = p["sector"],
            shares        = p["shares"],
            buy_price     = p["buy_price"],
            buy_date      = p["buy_date"],
            current_price = p["current_price"],
            currency      = p.get("currency", "USD"),
            cost_basis    = p["cost_basis"],
            current_value = p["current_value"],
            pnl           = p["pnl"],
            pnl_pct       = p["pnl_pct"],
            notes         = p.get("notes", ""),
            score         = p.get("score"),
        )
        for p in result["positions"]
    ]

    # portfolio.py zwraca totals jako zagnieżdżony dict
    totals = result.get("totals") or {}

    return PortfolioResponse(
        positions            = positions,
        total_value          = totals.get("total_value", 0.0),
        total_pnl            = totals.get("total_pnl", 0.0),
        total_pnl_pct        = totals.get("total_pnl_pct", 0.0),
        base_currency        = totals.get("base_currency", "PLN"),
        allocation_by_sector = result.get("allocation_by_sector", {}),
        benchmark            = result.get("benchmark"),
        warnings             = result.get("warnings", []),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add position",
)
async def add_position(payload: PositionAddRequest, user_id: CurrentUser) -> dict:
    # database.add_position wymaga buy_date jako string — jeśli klient
    # go nie poda, użyj dzisiejszej daty zamiast przekazywać None.
    from datetime import date
    buy_date = payload.buy_date or date.today().isoformat()

    db.add_position(
        user_id    = user_id,
        ticker     = payload.ticker.upper().strip(),
        shares     = payload.shares,
        buy_price  = payload.buy_price,
        buy_date   = buy_date,
        notes      = payload.notes or "",
    )
    return {"message": "Pozycja dodana"}


@router.delete(
    "/{position_id}",
    summary="Remove position",
)
async def remove_position(position_id: int, user_id: CurrentUser) -> dict:
    # database.remove_position nie zwraca informacji o sukcesie (brak wyjątku
    # przy nieistniejącym id — DELETE po prostu nic nie usuwa). Sprawdzamy
    # więc jawnie, czy pozycja istniała PRZED usunięciem, żeby móc zwrócić 404.
    existing = [p for p in db.get_portfolio(user_id) if p["id"] == position_id]
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pozycja nie znaleziona",
        )
    db.remove_position(position_id, user_id)
    return {"message": "Pozycja usunięta"}


@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk import positions (e.g. from XTB CSV)",
)
async def import_positions(payload: PortfolioImportRequest, user_id: CurrentUser) -> dict:
    """Importuje wiele pozycji naraz (parsowanie CSV robi frontend —
    tu tylko walidacja przez schemat i zapis). Zwraca podsumowanie."""
    from datetime import date
    added, errors = 0, []

    for pos in payload.positions:
        try:
            db.add_position(
                user_id   = user_id,
                ticker    = pos.ticker.upper().strip(),
                shares    = pos.shares,
                buy_price = pos.buy_price,
                buy_date  = pos.buy_date or date.today().isoformat(),
                notes     = pos.notes or "Import XTB",
            )
            added += 1
        except Exception as e:
            errors.append({"ticker": pos.ticker, "error": str(e)[:80]})

    return {"added": added, "errors": errors}


@router.get(
    "/correlation",
    summary="Correlation matrix between portfolio positions",
)
async def get_correlation(user_id: CurrentUser) -> dict:
    raw_positions = db.get_portfolio(user_id)
    tickers = [p["ticker"] for p in raw_positions]

    if len(tickers) < 2:
        return {
            "matrix": None, "high_pairs": [], "errors": [],
            "message": "Potrzeba co najmniej 2 pozycji do analizy korelacji.",
        }

    result = portfolio_logic.compute_correlation_matrix(tickers)

    matrix_dict = None
    if result["matrix"] is not None:
        matrix_dict = {
            row: {col: (None if (val := result["matrix"].loc[row, col]) != val  # NaN check
                        else round(float(val), 3))
                  for col in result["matrix"].columns}
            for row in result["matrix"].index
        }

    return {
        "matrix": matrix_dict,
        "high_pairs": [
            {"ticker_a": a, "ticker_b": b, "correlation": c}
            for a, b, c in result["high_pairs"]
        ],
        "errors": result["errors"],
    }
