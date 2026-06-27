# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /watchlist
  GET    /watchlist           — pobierz watchlistę
  POST   /watchlist           — dodaj ticker
  DELETE /watchlist/{ticker}  — usuń ticker
  PUT    /watchlist/{ticker}/alerts — ustaw alerty dla tickera
"""

from __future__ import annotations

import sys
import os

from fastapi import APIRouter, HTTPException, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from backend.core.security import CurrentUser
from backend.models.schemas import (
    WatchlistAddRequest,
    WatchlistAlertRequest,
    WatchlistItem,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get(
    "",
    response_model=list[WatchlistItem],
    summary="Get watchlist",
)
async def get_watchlist(user_id: CurrentUser) -> list[WatchlistItem]:
    """Pobiera watchlistę zalogowanego użytkownika."""
    entries = db.get_watchlist(user_id)
    return [
        WatchlistItem(
            ticker          = e["ticker"],
            last_score      = e.get("last_score"),
            alert_high      = e.get("alert_high"),
            alert_low       = e.get("alert_low"),
            alert_crossover = bool(e.get("alert_crossover", False)),
            added_at        = e.get("added_at"),
        )
        for e in entries
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add to watchlist",
)
async def add_to_watchlist(
    body:    WatchlistAddRequest,
    user_id: CurrentUser,
) -> dict:
    """
    Dodaje ticker do watchlisty.
    Nie weryfikuje czy ticker istnieje — weryfikacja po stronie klienta.
    """
    db.add_to_watchlist(body.ticker, user_id)
    return {"added": body.ticker, "user_id": user_id}


@router.delete(
    "/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from watchlist",
)
async def remove_from_watchlist(ticker: str, user_id: CurrentUser) -> None:
    """Usuwa ticker z watchlisty."""
    db.remove_from_watchlist(ticker.upper(), user_id)


@router.put(
    "/{ticker}/alerts",
    summary="Set alerts for ticker",
)
async def set_alerts(
    ticker:  str,
    body:    WatchlistAlertRequest,
    user_id: CurrentUser,
) -> dict:
    """
    Ustawia progi alertów dla danego tickera.
    - **alert_high**: powiadomienie gdy score DT > próg
    - **alert_low**: powiadomienie gdy score DT < próg
    - **alert_crossover**: powiadomienie przy złotym/czarnym krzyżu MA
    """
    db.set_watchlist_alerts(
        ticker.upper(),
        body.alert_high,
        body.alert_low,
        body.alert_crossover,
        user_id,
    )
    return {"ticker": ticker.upper(), "alerts_updated": True}


@router.post(
    "/{ticker}/score",
    summary="Update last score",
    include_in_schema=False,  # wewnętrzny endpoint (używany przez scheduler)
)
async def update_score(
    ticker:  str,
    score:   float,
    user_id: CurrentUser,
) -> dict:
    db.update_watchlist_score(ticker.upper(), score, user_id)
    return {"updated": True}
