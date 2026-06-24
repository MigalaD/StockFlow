# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Prognozowanie / scenariusze cenowe
=====================================
WAŻNE: to NIE są "prognozy" w sensie "cena będzie X". To narzędzia, które
pomagają zobaczyć ZAKRES możliwych scenariuszy na podstawie historycznych
danych - i jak szybko ten zakres się rozszerza, im dalej w przyszłość
patrzymy.

Modele:
- Monte Carlo / Geometric Brownian Motion (GBM) - standardowy model
  losowego błądzenia z dryfem, używany np. do wyceny opcji. Symuluje
  tysiące losowych ścieżek cen i pokazuje rozkład prawdopodobieństwa.
- Regresja liniowa na log-cenie - ekstrapolacja ostatniego trendu
  z przedziałem ufności.
- Wygładzanie wykładnicze Holta (poziom + trend) - klasyczna metoda
  prognozowania szeregów czasowych.

DLACZEGO TO NIE JEST "PRZEWIDYWANIE CENY":
Rynki akcji są w dużej mierze zgodne z hipotezą błądzenia losowego
(random walk) - najlepszym punktowym "przewidywaniem" ceny za N dni jest
często po prostu cena dzisiejsza. Te modele nie próbują pokonać tej
hipotezy - pokazują raczej, JAK SZEROKI jest realistyczny zakres wyników,
co samo w sobie jest użyteczną informacją (np. "czy mogę stracić 30% w
ciągu miesiąca, nawet jeśli długoterminowy trend jest dobry?").
"""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


# ----------------------------------------------------------------------
# MONTE CARLO / GBM
# ----------------------------------------------------------------------
def monte_carlo_forecast(
    df: pd.DataFrame,
    horizon_days: int = 30,
    n_sims: int = 2000,
    lookback_days: int = 252,
    seed: int | None = 42,
) -> dict:
    """
    Symuluje `n_sims` losowych ścieżek ceny na `horizon_days` dni w przód,
    metodą Geometric Brownian Motion: dS = mu*S*dt + sigma*S*dW.

    `mu` (dryf) i `sigma` (zmienność) są szacowane z dziennych log-zwrotów
    z ostatnich `lookback_days` dni.

    Zwraca:
    - dates: lista dat (dni handlowe) na horyzoncie
    - percentiles: dict {5, 25, 50, 75, 95} -> lista cen dla każdego dnia
    - final_prices: rozkład cen na koniec horyzontu (do histogramu)
    - stats: dict z mu, sigma (zannualizowane), prob_up, current_price,
      median_final, p5_final, p95_final
    """
    close = df["Close"].dropna()
    if len(close) < 30:
        return {"error": "Niewystarczająca ilość danych (potrzeba min. 30 dni)."}

    recent = close.tail(lookback_days)
    log_returns = np.log(recent / recent.shift(1)).dropna()

    mu_daily = log_returns.mean()
    sigma_daily = log_returns.std()

    current_price = float(close.iloc[-1])

    rng = np.random.default_rng(seed)
    # symulacja: dla kazdej sciezki, n kroków dziennych
    shocks = rng.normal(
        loc=(mu_daily - 0.5 * sigma_daily ** 2),
        scale=sigma_daily,
        size=(n_sims, horizon_days),
    )
    log_paths = np.cumsum(shocks, axis=1)
    price_paths = current_price * np.exp(log_paths)

    # dodaj punkt startowy (dzien 0 = cena dzisiejsza) dla wykresu
    price_paths_with_start = np.hstack([
        np.full((n_sims, 1), current_price), price_paths
    ])

    pct_levels = [5, 25, 50, 75, 95]
    percentiles = {
        p: np.percentile(price_paths_with_start, p, axis=0).tolist()
        for p in pct_levels
    }

    final_prices = price_paths[:, -1]
    prob_up = float((final_prices > current_price).mean() * 100)

    last_date = close.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=horizon_days + 1)

    return {
        "dates": future_dates,
        "percentiles": percentiles,
        "final_prices": final_prices,
        "stats": {
            "current_price": current_price,
            "mu_annualized_pct": float(mu_daily * TRADING_DAYS_PER_YEAR * 100),
            "sigma_annualized_pct": float(sigma_daily * np.sqrt(TRADING_DAYS_PER_YEAR) * 100),
            "prob_up_pct": prob_up,
            "median_final": float(np.median(final_prices)),
            "p5_final": float(np.percentile(final_prices, 5)),
            "p95_final": float(np.percentile(final_prices, 95)),
            "horizon_days": horizon_days,
            "lookback_days": len(recent),
        },
    }


# ----------------------------------------------------------------------
# TREND LINIOWY (regresja na log-cenie)
# ----------------------------------------------------------------------
def linear_trend_forecast(
    df: pd.DataFrame,
    horizon_days: int = 30,
    lookback_days: int = 90,
) -> dict:
    """
    Dopasowuje linię trendu (regresja liniowa) do log-ceny z ostatnich
    `lookback_days` dni i ekstrapoluje ją na `horizon_days` dni w przód,
    z przedziałem ufności 90% bazującym na odchyleniu reszt.

    Zwraca: dates, forecast (mediana), lower_90, upper_90, slope_pct_per_day
    """
    close = df["Close"].dropna()
    if len(close) < lookback_days:
        lookback_days = len(close)
    if lookback_days < 10:
        return {"error": "Niewystarczająca ilość danych do trendu."}

    recent = close.tail(lookback_days)
    y = np.log(recent.values)
    x = np.arange(len(y))

    # regresja liniowa metodą najmniejszych kwadratów
    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (slope * x + intercept)
    resid_std = residuals.std()

    last_date = recent.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=horizon_days + 1)
    future_x = np.arange(len(y) - 1, len(y) - 1 + len(future_dates))

    log_forecast = slope * future_x + intercept
    # przedzial ufnosci rozszerza sie z odleglosci od ostatniego punktu (sqrt(t))
    t_ahead = np.arange(len(future_dates))
    band_width = 1.645 * resid_std * np.sqrt(1 + t_ahead)  # ~90% CI

    forecast = np.exp(log_forecast)
    lower = np.exp(log_forecast - band_width)
    upper = np.exp(log_forecast + band_width)

    return {
        "dates": future_dates,
        "forecast": forecast.tolist(),
        "lower_90": lower.tolist(),
        "upper_90": upper.tolist(),
        "slope_pct_per_day": float((np.exp(slope) - 1) * 100),
        "lookback_days": lookback_days,
    }


# ----------------------------------------------------------------------
# WYGŁADZANIE WYKŁADNICZE HOLTA (poziom + trend)
# ----------------------------------------------------------------------
def holt_forecast(
    df: pd.DataFrame,
    horizon_days: int = 30,
    alpha: float = 0.3,
    beta: float = 0.05,
) -> dict:
    """
    Proste wygładzanie wykładnicze Holta (poziom + trend), implementacja
    manualna (bez statsmodels):

        level_t = alpha * y_t + (1 - alpha) * (level_{t-1} + trend_{t-1})
        trend_t = beta * (level_t - level_{t-1}) + (1 - beta) * trend_{t-1}

    `alpha` i `beta` to stałe wygładzania (0-1) - wyższe wartości = model
    szybciej reaguje na ostatnie zmiany, ale jest bardziej "nerwowy".

    Zwraca: dates, forecast (płaska linia poziom + trend * krok)
    """
    close = df["Close"].dropna()
    if len(close) < 10:
        return {"error": "Niewystarczająca ilość danych."}

    values = close.values
    level = values[0]
    trend = values[1] - values[0]

    for y in values[1:]:
        prev_level = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    last_date = close.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=horizon_days + 1)

    forecast = [level + trend * h for h in range(len(future_dates))]

    return {
        "dates": future_dates,
        "forecast": forecast,
        "level": float(level),
        "trend_per_day": float(trend),
    }


# ----------------------------------------------------------------------
# PODSUMOWANIE - tekstowa interpretacja dla UI
# ----------------------------------------------------------------------
def interpret_forecast(mc_stats: dict) -> str:
    prob_up = mc_stats["prob_up_pct"]
    horizon = mc_stats["horizon_days"]

    if prob_up >= 60:
        direction = f"model losowego błądzenia daje **{prob_up:.0f}%** szans, że cena za {horizon} dni będzie WYŻSZA niż dziś"
    elif prob_up <= 40:
        direction = f"model losowego błądzenia daje tylko **{prob_up:.0f}%** szans, że cena za {horizon} dni będzie WYŻSZA niż dziś"
    else:
        direction = f"model losowego błądzenia daje **{prob_up:.0f}%** szans na wzrost - blisko 'rzutu monetą'"

    return direction
