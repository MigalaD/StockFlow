# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /probability — Probability Engine (funkcja Premium).

Zwraca ROZKŁAD możliwych cen, nie prognozę punktową:
  - kwantyle na kilka horyzontów (fan chart)
  - prognozę zmienności (GARCH — z powrotem do średniej)
  - prawdopodobieństwo dotknięcia dowolnego poziomu (first-passage)
  - oczekiwany zakres dzienny
  - reżim zmienności na tle historii instrumentu

Każda prognoza jest LOGOWANA (forecast_log) do późniejszej weryfikacji.
Endpoint /probability/calibration pokazuje publicznie, jak często
deklarowane przedziały faktycznie zawierały cenę — to jest właściwy
produkt, nie same liczby.
"""

from __future__ import annotations

import os
import sys
import time
import logging
from datetime import date, timedelta

import numpy as np
from fastapi import APIRouter, HTTPException, Query, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
import probability_engine as pe
from stock_analyzer import fetch_history, sanitize_ticker
from backend.core.lang import RequestLang
from backend.core.security import OptionalCurrentUser

log = logging.getLogger("stockflow.probability")

probability_router = APIRouter(prefix="/probability", tags=["probability"])

_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_S = 30 * 60      # rozkład nie zmienia się co minutę
HORIZONS = [1, 5, 10, 20, 60]


@probability_router.get(
    "/calibration",
    summary="Public calibration table",
    description="Jak często deklarowane przedziały faktycznie zawierały cenę. Publiczne — to dowód, nie marketing.",
)
def calibration() -> dict:
    """Liczy faktyczne pokrycie przedziałów na rozstrzygniętych prognozach."""
    rows = db.get_calibration_data()
    if len(rows) < 30:
        return {
            "ready": False,
            "resolved_forecasts": len(rows),
            "message": (f"Zebrano {len(rows)} rozstrzygniętych prognoz (potrzeba min. 30). "
                        "Prognozy logują się automatycznie — tablica wypełni się z czasem."),
            "coverage": [],
        }

    import json as _json
    buckets = {50: [0, 0], 80: [0, 0], 90: [0, 0]}
    by_h: dict[int, list] = {}

    for r in rows:
        try:
            q = _json.loads(r["quantiles"])
        except (ValueError, TypeError):
            continue
        actual = r["actual_price"]
        pairs = {50: ("q25", "q75"), 80: ("q10", "q90"), 90: ("q5", "q95")}
        for lvl, (lo_k, hi_k) in pairs.items():
            if lo_k in q and hi_k in q:
                buckets[lvl][1] += 1
                if q[lo_k] <= actual <= q[hi_k]:
                    buckets[lvl][0] += 1
        by_h.setdefault(r["horizon_days"], []).append(1)

    coverage = [
        {"declared_pct": lvl,
         "actual_pct": round(hit / tot * 100, 1) if tot else None,
         "sample": tot}
        for lvl, (hit, tot) in sorted(buckets.items()) if tot > 0
    ]
    return {
        "ready": True,
        "resolved_forecasts": len(rows),
        "coverage": coverage,
        "by_horizon": {str(k): len(v) for k, v in sorted(by_h.items())},
        "model_version": pe.MODEL_VERSION,
    }


@probability_router.get(
    "/{ticker}",
    summary="Probability distribution for an instrument",
)
def get_probability(
    ticker: str,
    lang: RequestLang,
    level: float | None = Query(None, description="Poziom ceny do sprawdzenia prawdopodobieństwa dotknięcia"),
    drift: str = Query("zero", pattern="^(zero|shrink|historical)$"),
    _user: OptionalCurrentUser = None,
) -> dict:
    tkr = sanitize_ticker(ticker)
    key = f"{tkr}:{drift}"
    now = time.time()

    cached = _cache.get(key)
    if cached and (now - cached[0]) < _CACHE_TTL_S:
        base = dict(cached[1])
    else:
        try:
            import yfinance as yf
            df = fetch_history(yf.Ticker(tkr), period="2y")
        except Exception as e:
            log.warning("Probability: błąd pobierania %s: %s", tkr, e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Nie udało się pobrać danych rynkowych.")

        if df is None or df.empty or len(df) < 120 or "Close" not in df:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Za mało danych historycznych dla tego instrumentu (potrzeba ~6 miesięcy).")

        closes = df["Close"].to_numpy(float)
        closes = closes[np.isfinite(closes) & (closes > 0)]
        rets = np.diff(np.log(closes))
        last = float(closes[-1])

        sim = pe.simulate_paths(last, rets, horizon=max(HORIZONS),
                                n_sims=10000, drift_mode=drift, df_ohlc=df)
        if not sim:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Nie udało się zbudować rozkładu dla tego instrumentu.")

        paths = sim["paths"]
        bands = pe.quantile_bands(paths, HORIZONS)

        # Prawdopodobieństwa użyteczne decyzyjnie — bez pytania użytkownika
        moves = {}
        for pct in (5, 10, 20):
            up, dn = last * (1 + pct / 100), last * (1 - pct / 100)
            moves[f"up_{pct}pct_20d"] = pe.probability_of_touch(paths, last, up, 20)
            moves[f"down_{pct}pct_20d"] = pe.probability_of_touch(paths, last, dn, 20)

        garch = sim.get("garch")
        base = {
            "ticker": tkr,
            "last_price": round(last, 4),
            "model_version": pe.MODEL_VERSION,
            "drift_mode": drift,
            "bands": bands,
            "volatility": {
                "daily_pct": round(sim["sigma_daily_used"] * 100, 3),
                "annualized_pct": round(sim["sigma_daily_used"] * np.sqrt(pe.TRADING_DAYS) * 100, 2),
                "yang_zhang_pct": round(sim["sigma_yang_zhang"] * 100, 3) if sim.get("sigma_yang_zhang") else None,
                "ewma_pct": round(sim["sigma_ewma"] * 100, 3) if sim.get("sigma_ewma") else None,
                "forecast_path_pct": [round(float(x) * 100, 3) for x in sim["sigma_path"][:20]],
                "garch": {
                    "alpha": round(garch["alpha"], 4),
                    "beta": round(garch["beta"], 4),
                    "persistence": round(garch["persistence"], 4),
                    "longrun_daily_pct": round(garch["sigma_longrun"] * 100, 3),
                } if garch else None,
            },
            "regime": pe.volatility_regime(sim["sigma_daily_used"], rets),
            "daily_range": pe.expected_daily_range(df, sim["sigma_daily_used"], last),
            "move_probabilities": moves,
            "tail_fatness_nu": round(sim["nu"], 2),
            "assumptions": {
                "drift": drift,
                "distribution": "50% GARCH(1,1)+t-Student, 50% block bootstrap",
                "volatility_estimator": "Yang-Zhang (OHLC)" if sim.get("sigma_yang_zhang") else "EWMA",
                "simulations": 10000,
            },
        }
        _cache[key] = (now, base)

        # ── Etap 0: log do kalibracji (tylko raz na dzień na ticker) ──
        try:
            for b in bands:
                h = b["horizon_days"]
                db.log_forecast(
                    ticker=tkr,
                    target_date=(date.today() + timedelta(days=int(h * 1.4))).isoformat(),
                    horizon_days=h, last_price=last, quantiles=b["quantiles"],
                    model_version=pe.MODEL_VERSION,
                    sigma_daily=sim["sigma_daily_used"],
                )
        except Exception as e:
            log.warning("Probability: nie udało się zalogować prognozy: %s", e)

    # Zapytanie o konkretny poziom liczymy poza cache (parametr użytkownika),
    # ale bez ponownej symulacji — korzystamy z kwantyli już policzonych.
    if level and level > 0:
        base["level_query"] = _touch_from_bands(base, float(level))
    return base


def _touch_from_bands(payload: dict, level: float) -> dict:
    """Szacuje prawdopodobieństwo dotknięcia poziomu na podstawie
    zapisanych kwantyli (bez trzymania w cache pełnych ścieżek, które
    zajmowałyby setki MB przy wielu instrumentach)."""
    last = payload["last_price"]
    out = []
    for b in payload["bands"]:
        q = b["quantiles"]
        xs = np.array([q["q5"], q["q10"], q["q25"], q["q50"], q["q75"], q["q90"], q["q95"]])
        ps = np.array([5, 10, 25, 50, 75, 90, 95], dtype=float)
        if level >= last:
            # P(cena końcowa >= level) z interpolacji, ~2x dla dotknięcia w trakcie
            p_end = 100 - float(np.interp(level, xs, ps))
        else:
            p_end = float(np.interp(level, xs, ps))
        p_touch = min(99.0, p_end * 1.8)   # przybliżenie zasady odbicia
        out.append({"horizon_days": b["horizon_days"],
                    "prob_end_beyond_pct": round(max(0.0, p_end), 1),
                    "prob_touch_pct": round(max(0.0, p_touch), 1)})
    return {"level": level, "by_horizon": out}
