# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /scan
  GET  /scan         — wyniki ostatniego skanu
  POST /scan         — uruchom nowy skan (background task)
  GET  /scan/status  — status bieżącego skanu

Router: /journal
  GET    /journal         — lista wpisów
  POST   /journal         — dodaj wpis
  DELETE /journal/{id}    — usuń wpis
"""

from __future__ import annotations

import sys
import os
import threading
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from scanner import scan_market
from tickers import (
    SKANER_USA, SKANER_GPW, SKANER_EUROPA,
    SKANER_KRYPTO, SKANER_WSZYSTKIE,
)
from backend.core.security import CurrentUser, OptionalCurrentUser
from backend.models.schemas import (
    JournalAddRequest,
    JournalItem,
    ScanRequest,
    ScanResponse,
    ScanResultItem,
)

# ── Scanner ────────────────────────────────────────────────────────────

scan_router = APIRouter(prefix="/scan", tags=["scanner"])

# Stan skanu żyje w BAZIE (db.set_scan_status / get_scan_status), nie w
# pamięci procesu. Uvicorn uruchamia kilka workerów — stan w pamięci
# istniał osobno w każdym z nich: POST /scan startował skan w workerze A,
# a status odpytywany był z workera B, który widział "nic nie działa".
# Frontend gasił panel, choć skan pracował dalej (stąd też 409 przy
# ponownym kliknięciu). Baza (jeden plik na kontener) jest współdzielona.
_scan_lock = threading.Lock()

# Jeśli running=True, ale ostatnia aktualizacja starsza niż tyle sekund,
# uznajemy skan za martwy (np. kontener zrestartował w połowie) i
# pozwalamy wystartować nowy zamiast blokować wiecznym 409.
_SCAN_STALE_AFTER_S = 180

_MARKET_MAP = {
    "usa":    SKANER_USA,
    "gpw":    SKANER_GPW,
    "europa": SKANER_EUROPA,
    "krypto": SKANER_KRYPTO,
    "all":    SKANER_WSZYSTKIE,
}


def _status_is_stale(updated_at: str | None) -> bool:
    if not updated_at:
        return True
    try:
        from datetime import datetime as _dt
        last = _dt.fromisoformat(updated_at)
        return (_dt.now() - last).total_seconds() > _SCAN_STALE_AFTER_S
    except (ValueError, TypeError):
        return True


def _run_scan_background(market: str) -> None:
    """Uruchamia skan w tle (background task FastAPI)."""
    tickers = _MARKET_MAP.get(market, SKANER_USA)
    started = time.time()

    db.set_scan_status({
        "running":    True,
        "progress":   0,
        "total":      len(tickers),
        "current":    "",
        "started_at": started,
    })

    def progress_cb(done: int, total: int, ticker: str) -> None:
        db.set_scan_status({
            "running":    True,
            "progress":   done,
            "total":      total,
            "current":    ticker,
            "started_at": started,
        })

    try:
        scan_market(tickers, progress_callback=progress_cb)
    finally:
        db.set_scan_status({
            "running":    False,
            "progress":   len(tickers),
            "total":      len(tickers),
            "current":    "",
            "started_at": started,
        })


@scan_router.get(
    "",
    response_model=ScanResponse,
    summary="Get last scan results",
)
async def get_scan_results(_user: OptionalCurrentUser = None) -> ScanResponse:
    """Zwraca wyniki ostatniego skanu. Publiczny endpoint."""
    results  = db.get_scan_results()
    scan_at  = db.get_last_scan_time() or ""

    return ScanResponse(
        results = [
            ScanResultItem(
                ticker   = r["ticker"],
                name     = r.get("name"),
                sector   = r.get("sector"),
                price    = r.get("price"),
                score    = r["score"],
                score_st = r.get("score_st"),
            )
            for r in results
        ],
        scanned_at = scan_at,
        total      = len(results),
    )


@scan_router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start new scan",
)
async def start_scan(
    body:             ScanRequest,
    background_tasks: BackgroundTasks,
    user_id:          CurrentUser,
) -> dict:
    """
    Uruchamia skan w tle. Zwraca natychmiast z 202 Accepted.
    Postęp dostępny przez GET /scan/status.
    Wyniki dostępne przez GET /scan gdy skan się zakończy.
    """
    with _scan_lock:
        state, updated_at = db.get_scan_status()
        if state.get("running") and not _status_is_stale(updated_at):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scan already running",
            )

    background_tasks.add_task(_run_scan_background, body.market)
    tickers_count = len(_MARKET_MAP.get(body.market, SKANER_USA))

    return {
        "status":  "accepted",
        "market":  body.market,
        "tickers": tickers_count,
        "message": f"Scan started for {tickers_count} instruments",
    }


@scan_router.get(
    "/status",
    summary="Scan progress",
)
async def scan_status() -> dict:
    """Zwraca aktualny status bieżącego skanu (stan współdzielony w bazie)."""
    state, updated_at = db.get_scan_status()

    # Skan oznaczony jako running, ale dawno nieaktualizowany = martwy
    # (np. restart kontenera w połowie). Raportuj jako zakończony.
    if state.get("running") and _status_is_stale(updated_at):
        state["running"] = False

    elapsed = None
    if state["started_at"]:
        elapsed = round(time.time() - state["started_at"], 1)

    pct = 0
    if state["total"] > 0:
        pct = round(state["progress"] / state["total"] * 100)

    return {
        "running":     state["running"],
        "progress":    state["progress"],
        "total":       state["total"],
        "percent":     pct,
        "current":     state["current"],
        "elapsed_s":   elapsed,
    }


# ── Journal ────────────────────────────────────────────────────────────

journal_router = APIRouter(prefix="/journal", tags=["journal"])


@journal_router.get(
    "",
    response_model=list[JournalItem],
    summary="Get journal entries",
)
async def get_journal(
    user_id: CurrentUser,
    ticker:  str | None = Query(None, max_length=20),
) -> list[JournalItem]:
    """Pobiera wpisy z dziennika. Opcjonalnie filtruje po tickerze."""
    entries = db.get_journal_entries(
        user_id,
        ticker=ticker.upper() if ticker else None,
    )
    return [
        JournalItem(
            id         = e["id"],
            entry_date = e["entry_date"],
            ticker     = e["ticker"],
            decision   = e["decision"],
            reason     = e["reason"],
            score      = e.get("score"),
            price      = e.get("price"),
            created_at = e.get("created_at"),
        )
        for e in entries
    ]


@journal_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add journal entry",
)
async def add_journal_entry(
    body:    JournalAddRequest,
    user_id: CurrentUser,
) -> dict:
    """Dodaje wpis do dziennika inwestycyjnego."""
    db.add_journal_entry(
        user_id    = user_id,
        entry_date = body.entry_date,
        ticker     = body.ticker,
        decision   = body.decision,
        reason     = body.reason,
        score      = body.score or 0,
        price      = body.price or 0,
    )
    return {"added": True, "ticker": body.ticker}


@journal_router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete journal entry",
)
async def delete_journal_entry(
    entry_id: int,
    user_id:  CurrentUser,
) -> None:
    db.delete_journal_entry(entry_id, user_id)
