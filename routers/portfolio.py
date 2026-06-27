# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /portfolio
  GET    /portfolio              — pobierz portfolio z P&L
  POST   /portfolio              — dodaj pozycję
  DELETE /portfolio/{id}         — usuń pozycję
"""

from __future__ import annotations

import sys
import os

from fastapi import APIRouter, HTTPException, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from portfolio import analyze_portfolio
from stock_analyzer import analyze_ticker
from backend.core.security import CurrentUser
from backend.models.schemas import (
    PortfolioResponse,
    PositionAddRequest,
    PositionItem,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get portfolio with P&L",
)
async def get_portfolio(user_id: CurrentUser) -> PortfolioResponse:
    """
    Pobiera portfolio zalogowanego użytkownika z wyliczonym P&L,
    alokacją sektorową i ostrzeżeniami o korelacji.

    Dane cenowe pobierane z Yahoo Finance (cache 15 min).
    """
    try:
        result = analyze_portfolio(user_id, analyze_ticker)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Portfolio analysis failed: {e}")

    positions = [
        PositionItem(
            id            = p["id"],
            ticker        = p["ticker"],
            name          = p.get("name", p["ticker"]),
            shares        = p["shares"],
            buy_price     = p["buy_price"],
            current_price = p.get("current_price", 0.0),
            current_value = p.get("current_value", 0.0),
            pnl           = p.get("pnl", 0.0),
            pnl_pct       = p.get("pnl_pct", 0.0),
            currency      = p.get("currency", "USD"),
            sector        = p.get("sector", "Nieznany"),
            buy_date      = p.get("buy_date"),
            notes         = p.get("notes"),
            score         = p.get("score"),
        )
        for p in result.get("positions", [])
    ]

    # portfolio.py zwraca totals jako zagnieżdżony dict
    totals = result.get("totals") or {}

    return PortfolioResponse(
        positions            = positions,
        total_value          = totals.get("total_value", 0.0),
        total_pnl            = totals.get("total_pnl", 0.0),
        total_pnl_pct        = totals.get("total_pnl_pct", 0.0),
        allocation_by_sector = result.get("allocation_by_sector", {}),
        warnings             = result.get("warnings", []),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add position",
)
async def add_position(
    body:    PositionAddRequest,
    user_id: CurrentUser,
) -> dict:
    """Dodaje nową pozycję do portfolio."""
    try:
        db.add_position(
            user_id   = user_id,
            ticker    = body.ticker,
            shares    = body.shares,
            buy_price = body.buy_price,
            buy_date  = body.buy_date,
            notes     = body.notes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"added": body.ticker, "shares": body.shares}


@router.delete(
    "/{position_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove position",
)
async def remove_position(
    position_id: int,
    user_id:     CurrentUser,
) -> None:
    """Usuwa pozycję z portfolio."""
    db.remove_position(position_id, user_id)
