# Copyright (c) 2026 Damian Migała / StockFlow

"""
Probability Engine — rdzeń probabilistyczny (Warstwa 1).

CO TO ROBI, A CZEGO NIE:
NIE przewiduje ceny. Buduje ROZKŁAD możliwych cen i zwraca skalibrowane
prawdopodobieństwa ("80% szans na zakres 180-194 zł w 5 dni"), które da
się potem zweryfikować na danych (patrz forecast_log w database.py).

CO POPRAWIA WZGLĘDEM STAREGO monte_carlo_forecast():
1. Zmienność z estymatora Yang-Zhang (pełne OHLC) zamiast odchylenia
   z samych zamknięć — 5-8x efektywniejszy statystycznie na tej samej próbce.
2. Zmienność DYNAMICZNA (EWMA / GARCH(1,1)) zamiast stałej — uwzględnia
   klastrowanie zmienności i powrót do średniej.
3. Szoki z rozkładu t-Studenta (grube ogony) oraz block bootstrap
   z historii — zamiast rozkładu normalnego, który zaniża ryzyko.
4. Dryf domyślnie ZEROWY — szacowanie mu z historii to w praktyce szum.

ZALEŻNOŚCI: wyłącznie numpy i pandas (świadomie — bez scipy/arch, żeby
nie dokładać bibliotek do deployu; GARCH liczony własnym MLE na numpy).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
MODEL_VERSION = "pe-1.0.0"   # zmiana = nowa wersja w forecast_log (kalibracja liczona osobno)


# ──────────────────────────────────────────────────────────────────────
# 1. ESTYMATORY ZMIENNOŚCI Z OHLC
# ──────────────────────────────────────────────────────────────────────

def yang_zhang_volatility(df: pd.DataFrame, window: int = 30) -> float | None:
    """Zmienność dzienna wg estymatora Yang-Zhang.

    Łączy trzy komponenty: zmienność overnight (luka otwarcia), open-to-close
    oraz Rogers-Satchell (odporny na dryf). Najlepszy ogólnego przeznaczenia
    estymator z OHLC — wykorzystuje całą świecę, nie tylko zamknięcie.
    """
    need = {"Open", "High", "Low", "Close"}
    if not need.issubset(df.columns) or len(df) < window + 2:
        return None

    d = df.tail(window + 1).copy()
    o, h, l, c = d["Open"].to_numpy(float), d["High"].to_numpy(float), \
                 d["Low"].to_numpy(float), d["Close"].to_numpy(float)
    if np.any(o <= 0) or np.any(c <= 0) or np.any(h <= 0) or np.any(l <= 0):
        return None

    # overnight: log(open_t / close_{t-1})
    ov = np.log(o[1:] / c[:-1])
    # open-to-close: log(close_t / open_t)
    oc = np.log(c[1:] / o[1:])
    # Rogers-Satchell (na tych samych świecach co powyżej)
    hi, lo, op, cl = h[1:], l[1:], o[1:], c[1:]
    rs = (np.log(hi / cl) * np.log(hi / op)) + (np.log(lo / cl) * np.log(lo / op))

    n = len(ov)
    if n < 5:
        return None

    var_ov = np.var(ov, ddof=1)
    var_oc = np.var(oc, ddof=1)
    var_rs = np.mean(rs)

    # k minimalizuje wariancję estymatora (wzór z oryginalnej pracy)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    var_yz = var_ov + k * var_oc + (1 - k) * var_rs

    if not np.isfinite(var_yz) or var_yz <= 0:
        return None
    return float(np.sqrt(var_yz))


def parkinson_volatility(df: pd.DataFrame, window: int = 30) -> float | None:
    """Zmienność dzienna wg Parkinsona (tylko High-Low). Fallback dla YZ."""
    if not {"High", "Low"}.issubset(df.columns) or len(df) < window:
        return None
    d = df.tail(window)
    h, l = d["High"].to_numpy(float), d["Low"].to_numpy(float)
    if np.any(h <= 0) or np.any(l <= 0):
        return None
    var = np.mean(np.log(h / l) ** 2) / (4 * np.log(2))
    return float(np.sqrt(var)) if np.isfinite(var) and var > 0 else None


# ──────────────────────────────────────────────────────────────────────
# 2. DYNAMIKA ZMIENNOŚCI
# ──────────────────────────────────────────────────────────────────────

def ewma_volatility(returns: np.ndarray, lam: float = 0.94) -> float | None:
    """Zmienność EWMA (RiskMetrics). Reaguje na ostatnie szoki szybciej
    niż zwykłe odchylenie standardowe."""
    r = returns[np.isfinite(returns)]
    if len(r) < 10:
        return None
    var = np.var(r[:10], ddof=1)
    for x in r[10:]:
        var = lam * var + (1 - lam) * x * x
    return float(np.sqrt(var)) if var > 0 else None


def fit_garch11(returns: np.ndarray, max_iter: int = 60) -> dict | None:
    """GARCH(1,1) dopasowany własnym MLE (numpy, bez scipy/arch).

    Model: sigma2_t = omega + alpha * r_{t-1}^2 + beta * sigma2_{t-1}

    Kluczowa wartość dodana wobec EWMA: parametr omega daje POWRÓT DO
    ŚREDNIEJ — po szoku zmienność opada ku długoterminowej wartości
    zamiast pozostać wysoka w nieskończoność. To istotne dla horyzontów
    5-20 dni, gdzie EWMA systematycznie przeszacowuje ryzyko po krachu.

    Optymalizacja: przeszukiwanie siatki + lokalne zawężanie (model ma
    tylko 2 wolne parametry po reparametryzacji, więc to wystarcza
    i jest znacznie stabilniejsze niż gradient bez scipy).
    """
    r = returns[np.isfinite(returns)]
    if len(r) < 100:
        return None
    r = r - r.mean()
    var_uncond = float(np.var(r, ddof=1))
    if var_uncond <= 0:
        return None

    def neg_loglik(alpha: float, beta: float) -> float:
        if alpha <= 0 or beta <= 0 or alpha + beta >= 0.999:
            return np.inf
        omega = var_uncond * (1 - alpha - beta)
        if omega <= 0:
            return np.inf
        sigma2 = var_uncond
        ll = 0.0
        for x in r:
            ll += np.log(sigma2) + (x * x) / sigma2
            sigma2 = omega + alpha * x * x + beta * sigma2
            if sigma2 <= 0 or not np.isfinite(sigma2):
                return np.inf
        return ll

    best = (np.inf, 0.08, 0.90)
    for a in np.linspace(0.02, 0.25, 9):
        for b in np.linspace(0.60, 0.97, 9):
            if a + b >= 0.999:
                continue
            v = neg_loglik(a, b)
            if v < best[0]:
                best = (v, a, b)

    # lokalne zawężanie wokół najlepszego punktu
    _, a0, b0 = best
    for scale in (0.05, 0.02, 0.008):
        for a in np.linspace(max(0.005, a0 - scale), min(0.3, a0 + scale), 7):
            for b in np.linspace(max(0.4, b0 - scale), min(0.985, b0 + scale), 7):
                if a + b >= 0.999:
                    continue
                v = neg_loglik(a, b)
                if v < best[0]:
                    best = (v, a, b)
        _, a0, b0 = best

    _, alpha, beta = best
    omega = var_uncond * (1 - alpha - beta)

    # bieżąca wariancja warunkowa (przejście po całej próbce)
    sigma2 = var_uncond
    for x in r:
        sigma2 = omega + alpha * x * x + beta * sigma2

    return {
        "omega": float(omega), "alpha": float(alpha), "beta": float(beta),
        "sigma_current": float(np.sqrt(sigma2)),
        "sigma_longrun": float(np.sqrt(var_uncond)),
        "persistence": float(alpha + beta),
    }


def garch_forecast_path(params: dict, horizon: int) -> np.ndarray:
    """Prognoza dziennej zmienności na kolejne `horizon` dni z GARCH.

    Zwraca wektor sigma_t (nie sigma^2). Pokazuje powrót do średniej:
    po szoku kolejne dni mają malejącą oczekiwaną zmienność.
    """
    omega, alpha, beta = params["omega"], params["alpha"], params["beta"]
    sigma2 = params["sigma_current"] ** 2
    out = []
    for _ in range(horizon):
        sigma2 = omega + (alpha + beta) * sigma2
        out.append(np.sqrt(max(sigma2, 1e-12)))
    return np.array(out)


# ──────────────────────────────────────────────────────────────────────
# 3. SYMULACJA
# ──────────────────────────────────────────────────────────────────────

def _fit_student_t_df(returns: np.ndarray) -> float:
    """Szacuje stopnie swobody t-Studenta metodą momentów (kurtoza).

    Dla t-Studenta: kurtoza nadmiarowa = 6/(df-4), df>4.
    Ograniczamy do [3, 30] — poniżej 3 wariancja nie istnieje,
    powyżej 30 rozkład jest praktycznie normalny.
    """
    r = returns[np.isfinite(returns)]
    if len(r) < 30:
        return 6.0
    r = (r - r.mean()) / (r.std(ddof=1) + 1e-12)
    kurt_excess = float(np.mean(r ** 4) - 3.0)
    if kurt_excess <= 0.1:
        return 30.0
    df = 4.0 + 6.0 / kurt_excess
    return float(np.clip(df, 3.0, 30.0))


def simulate_paths(
    last_price: float,
    returns: np.ndarray,
    horizon: int,
    n_sims: int = 10000,
    drift_mode: str = "zero",
    seed: int | None = 42,
    df_ohlc: pd.DataFrame | None = None,
) -> dict:
    """Generuje ścieżki cen mieszanką dwóch metod.

    Połowa ścieżek: GARCH(1,1) + szoki t-Studenta (parametryczna).
    Połowa ścieżek: block bootstrap historycznych zwrotów (nieparametryczna,
    zachowuje realne sekwencje i autokorelację).

    Mieszanka uśrednia słabości obu podejść: GARCH może źle trafić
    z rozkładem, bootstrap nie ekstrapoluje poza to, co już było.
    """
    rng = np.random.default_rng(seed)
    r = returns[np.isfinite(returns)]
    if len(r) < 60 or last_price <= 0 or horizon < 1:
        return {}

    # ── Poziom zmienności: preferuj Yang-Zhang (OHLC), fallback na zwroty ──
    sigma_yz = yang_zhang_volatility(df_ohlc) if df_ohlc is not None else None
    sigma_ewma = ewma_volatility(r)
    garch = fit_garch11(r)

    # ── Dryf ──
    mu_hist = float(np.mean(r))
    if drift_mode == "historical":
        mu = mu_hist
    elif drift_mode == "shrink":
        mu = 0.2 * mu_hist
    else:                       # "zero" — domyślny, najuczciwszy
        mu = 0.0

    n_half = n_sims // 2
    nu = _fit_student_t_df(r)

    # ── A. Ścieżki parametryczne: GARCH + t-Studenta ──
    if garch:
        sigma_path = garch_forecast_path(garch, horizon)
        # zakotwicz poziom na Yang-Zhang, jeśli dostępny (lepszy estymator
        # poziomu), zachowując KSZTAŁT krzywej z GARCH
        if sigma_yz and garch["sigma_current"] > 0:
            sigma_path = sigma_path * (sigma_yz / garch["sigma_current"])
    else:
        base = sigma_yz or sigma_ewma or float(np.std(r, ddof=1))
        sigma_path = np.full(horizon, base)

    # standaryzowane szoki t (wariancja 1)
    t_raw = rng.standard_t(nu, size=(n_half, horizon))
    t_std = t_raw / np.sqrt(nu / (nu - 2.0)) if nu > 2 else t_raw
    shocks_param = mu - 0.5 * sigma_path ** 2 + sigma_path * t_std

    # ── B. Ścieżki bootstrapowe (bloki 5-dniowe) ──
    block = 5
    n_blocks = int(np.ceil(horizon / block))
    max_start = len(r) - block
    starts = rng.integers(0, max_start, size=(n_sims - n_half, n_blocks))
    boot = np.concatenate(
        [r[starts[:, i][:, None] + np.arange(block)] for i in range(n_blocks)], axis=1
    )[:, :horizon]
    if drift_mode == "zero":
        boot = boot - mu_hist          # usuń historyczny dryf
    elif drift_mode == "shrink":
        boot = boot - 0.8 * mu_hist

    log_paths = np.concatenate([shocks_param, boot], axis=0)
    price_paths = last_price * np.exp(np.cumsum(log_paths, axis=1))

    return {
        "paths": price_paths,
        "sigma_path": sigma_path,
        "sigma_daily_used": float(sigma_path[0]),
        "nu": nu,
        "garch": garch,
        "sigma_yang_zhang": sigma_yz,
        "sigma_ewma": sigma_ewma,
        "mu_daily": mu,
    }


# ──────────────────────────────────────────────────────────────────────
# 4. WYJŚCIA UŻYTKOWE
# ──────────────────────────────────────────────────────────────────────

QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def quantile_bands(paths: np.ndarray, horizons: list[int]) -> list[dict]:
    """Kwantyle ceny dla zadanych horyzontów (fan chart)."""
    out = []
    n_days = paths.shape[1]
    for h in horizons:
        if h > n_days:
            continue
        col = paths[:, h - 1]
        out.append({
            "horizon_days": h,
            "quantiles": {f"q{int(q*100)}": round(float(np.quantile(col, q)), 4)
                          for q in QUANTILES},
        })
    return out


def probability_of_touch(paths: np.ndarray, last_price: float,
                         level: float, horizon: int | None = None) -> float:
    """Prawdopodobieństwo DOTKNIĘCIA poziomu w dowolnym momencie horyzontu.

    Uwaga: to nie to samo co prawdopodobieństwo zamknięcia powyżej/poniżej.
    Dla stop-lossa liczy się właśnie dotknięcie — dlatego sprawdzamy całą
    ścieżkę, nie tylko punkt końcowy (first-passage).
    """
    p = paths if horizon is None else paths[:, :horizon]
    hit = (p >= level).any(axis=1) if level > last_price else (p <= level).any(axis=1)
    return round(float(np.mean(hit)) * 100, 2)


def expected_daily_range(df: pd.DataFrame, sigma_daily: float,
                         last_price: float) -> dict:
    """Oczekiwany zakres dzienny — to JEST przewidywalne (w odróżnieniu
    od ceny otwarcia/zamknięcia). Bazuje na zmienności i historycznym
    stosunku zakresu do zmienności."""
    res = {"expected_range_pct": round(float(sigma_daily * 100), 2)}
    if {"High", "Low"}.issubset(df.columns) and len(df) >= 20:
        d = df.tail(60)
        rng_pct = ((d["High"] - d["Low"]) / d["Close"]).to_numpy(float)
        rng_pct = rng_pct[np.isfinite(rng_pct)]
        if len(rng_pct) > 5:
            res["median_range_pct"] = round(float(np.median(rng_pct) * 100), 2)
            res["p90_range_pct"] = round(float(np.quantile(rng_pct, 0.9) * 100), 2)
            res["expected_range_abs"] = round(float(np.median(rng_pct) * last_price), 2)
    return res


def volatility_regime(sigma_daily: float, returns: np.ndarray) -> dict:
    """Klasyfikuje bieżącą zmienność na tle własnej historii instrumentu.

    Percentyl mówi więcej niż wartość bezwzględna: 2% dziennie to dużo
    dla spółki dywidendowej, a mało dla krypto."""
    r = returns[np.isfinite(returns)]
    if len(r) < 120:
        return {"label": "nieznany", "percentile": None}
    roll = pd.Series(r).rolling(20).std().dropna().to_numpy()
    if len(roll) < 20:
        return {"label": "nieznany", "percentile": None}
    pct = float(np.mean(roll < sigma_daily) * 100)
    label = ("ekstremalna" if pct >= 90 else "wysoka" if pct >= 70
             else "normalna" if pct >= 30 else "niska")
    return {
        "label": label,
        "percentile": round(pct, 1),
        "annualized_pct": round(float(sigma_daily * np.sqrt(TRADING_DAYS) * 100), 2),
    }
