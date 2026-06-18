"""
Testy dla forecasting.py
==========================
Sprawdzają, czy modele scenariuszy cenowych (Monte Carlo/GBM, trend
liniowy, Holt) zwracają sensowne, wewnętrznie spójne struktury danych
na syntetycznych danych (offline).
"""

import numpy as np
import pandas as pd

import forecasting as fc


def _make_df(n=300, seed=0, drift=0.0003, vol=0.015):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    returns = rng.normal(drift, vol, size=n)
    prices = 100 * np.cumprod(1 + returns)
    return pd.DataFrame({"Close": prices}, index=dates)


# ----------------------------------------------------------------------
# MONTE CARLO
# ----------------------------------------------------------------------
def test_monte_carlo_basic_structure():
    df = _make_df()
    result = fc.monte_carlo_forecast(df, horizon_days=30, n_sims=500)

    assert "error" not in result
    assert len(result["dates"]) == 31  # horyzont + dzień startowy
    for p in (5, 25, 50, 75, 95):
        assert p in result["percentiles"]
        assert len(result["percentiles"][p]) == 31

    stats = result["stats"]
    assert stats["current_price"] > 0
    assert 0 <= stats["prob_up_pct"] <= 100
    assert stats["horizon_days"] == 30


def test_monte_carlo_percentiles_ordered():
    """Percentyle powinny być uporządkowane: p5 <= p25 <= p50 <= p75 <= p95
    dla każdego dnia (z definicji percentyla)."""
    df = _make_df(seed=1)
    result = fc.monte_carlo_forecast(df, horizon_days=20, n_sims=1000)

    p = result["percentiles"]
    for day in range(len(p[5])):
        assert p[5][day] <= p[25][day] <= p[50][day] <= p[75][day] <= p[95][day]


def test_monte_carlo_uncertainty_grows_with_horizon():
    """Zakres 5-95 percentyla powinien być szerszy dla dłuższego horyzontu
    niż dla krótszego (rosnąca niepewność w czasie)."""
    df = _make_df(seed=2)
    short = fc.monte_carlo_forecast(df, horizon_days=10, n_sims=2000, seed=42)
    long = fc.monte_carlo_forecast(df, horizon_days=60, n_sims=2000, seed=42)

    short_range = short["percentiles"][95][-1] - short["percentiles"][5][-1]
    long_range = long["percentiles"][95][-1] - long["percentiles"][5][-1]

    assert long_range > short_range


def test_monte_carlo_zero_volatility_collapses_range():
    """Przy zerowej zmienności wszystkie ścieżki powinny być identyczne."""
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": [100.0] * n}, index=dates)

    result = fc.monte_carlo_forecast(df, horizon_days=10, n_sims=100)
    p5 = result["percentiles"][5][-1]
    p95 = result["percentiles"][95][-1]
    assert abs(p95 - p5) < 1e-6


def test_monte_carlo_insufficient_data():
    df = pd.DataFrame({"Close": [100.0, 101.0, 99.0]},
                       index=pd.date_range("2024-01-01", periods=3))
    result = fc.monte_carlo_forecast(df, horizon_days=10)
    assert "error" in result


# ----------------------------------------------------------------------
# TREND LINIOWY
# ----------------------------------------------------------------------
def test_linear_trend_forecast_structure():
    df = _make_df()
    result = fc.linear_trend_forecast(df, horizon_days=30, lookback_days=90)

    assert "error" not in result
    assert len(result["dates"]) == 31
    assert len(result["forecast"]) == 31
    assert len(result["lower_90"]) == 31
    assert len(result["upper_90"]) == 31

    # przedzial ufnosci powinien zawierac prognoze (lower <= forecast <= upper)
    for f, lo, hi in zip(result["forecast"], result["lower_90"], result["upper_90"]):
        assert lo <= f <= hi


def test_linear_trend_band_widens_over_time():
    df = _make_df(seed=3)
    result = fc.linear_trend_forecast(df, horizon_days=30, lookback_days=90)

    width_start = result["upper_90"][1] - result["lower_90"][1]
    width_end = result["upper_90"][-1] - result["lower_90"][-1]
    assert width_end > width_start


def test_linear_trend_detects_uptrend():
    n = 150
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    prices = 100 * np.exp(np.linspace(0, 0.5, n))  # czysty trend wzrostowy
    df = pd.DataFrame({"Close": prices}, index=dates)

    result = fc.linear_trend_forecast(df, horizon_days=10, lookback_days=100)
    assert result["slope_pct_per_day"] > 0


def test_linear_trend_insufficient_data():
    df = pd.DataFrame({"Close": [100.0, 101.0]},
                       index=pd.date_range("2024-01-01", periods=2))
    result = fc.linear_trend_forecast(df, horizon_days=10)
    assert "error" in result


# ----------------------------------------------------------------------
# HOLT
# ----------------------------------------------------------------------
def test_holt_forecast_structure():
    df = _make_df()
    result = fc.holt_forecast(df, horizon_days=20)

    assert "error" not in result
    assert len(result["dates"]) == 21
    assert len(result["forecast"]) == 21
    assert isinstance(result["level"], float)
    assert isinstance(result["trend_per_day"], float)


def test_holt_flat_series_has_zero_trend():
    n = 50
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": [100.0] * n}, index=dates)

    result = fc.holt_forecast(df, horizon_days=10)
    assert abs(result["trend_per_day"]) < 1e-9
    assert all(abs(f - 100.0) < 1e-6 for f in result["forecast"])


def test_holt_insufficient_data():
    df = pd.DataFrame({"Close": [100.0]}, index=pd.date_range("2024-01-01", periods=1))
    result = fc.holt_forecast(df, horizon_days=10)
    assert "error" in result


# ----------------------------------------------------------------------
# INTERPRETACJA
# ----------------------------------------------------------------------
def test_interpret_forecast_text():
    stats_up = {"prob_up_pct": 70, "horizon_days": 30}
    stats_down = {"prob_up_pct": 30, "horizon_days": 30}
    stats_neutral = {"prob_up_pct": 50, "horizon_days": 30}

    assert "WYŻSZA" in fc.interpret_forecast(stats_up)
    assert "WYŻSZA" in fc.interpret_forecast(stats_down)
    assert "rzutu monetą" in fc.interpret_forecast(stats_neutral)
