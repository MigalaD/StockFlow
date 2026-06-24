"""
Testy dla intraday_signals.py
================================
Sprawdzają ATR, Stochastik, OBV (+ dywergencja) i wykrywanie poziomów
wsparcia/oporu na syntetycznych danych OHLCV (bez sieci).
"""
import numpy as np
import pandas as pd

from intraday_signals import (
    compute_atr,
    atr_summary,
    compute_stochastic,
    stochastic_summary,
    compute_obv,
    detect_obv_divergence,
    detect_support_resistance,
)


def _make_ohlcv(n=200, seed=1, trend=0.0005, vol=0.02):
    """Buduje syntetyczny DataFrame OHLCV do testów."""
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(trend, vol, n))
    high = close * (1 + np.abs(rng.normal(0, 0.01, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.01, n)))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": close, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


# ----------------------------------------------------------------------
# ATR
# ----------------------------------------------------------------------
def test_compute_atr_returns_series_same_length():
    df = _make_ohlcv()
    atr = compute_atr(df)
    assert len(atr) == len(df)
    assert atr.dropna().min() >= 0  # ATR nie może być ujemny


def test_atr_summary_structure():
    df = _make_ohlcv()
    summary = atr_summary(df)
    assert summary is not None
    assert set(summary.keys()) == {"atr", "atr_pct", "price"}
    assert summary["atr"] >= 0
    assert summary["atr_pct"] >= 0


def test_atr_summary_none_on_empty():
    assert atr_summary(pd.DataFrame()) is None


def test_atr_summary_none_on_insufficient_data():
    df = _make_ohlcv(n=5)
    assert atr_summary(df) is None


def test_atr_missing_columns_returns_empty_series():
    df = pd.DataFrame({"Close": [1, 2, 3]})
    atr = compute_atr(df)
    assert atr.isna().all()


def test_higher_volatility_gives_higher_atr():
    calm = _make_ohlcv(seed=5, vol=0.005)
    wild = _make_ohlcv(seed=5, vol=0.05)
    calm_summary = atr_summary(calm)
    wild_summary = atr_summary(wild)
    assert wild_summary["atr_pct"] > calm_summary["atr_pct"]


# ----------------------------------------------------------------------
# STOCHASTIK
# ----------------------------------------------------------------------
def test_compute_stochastic_returns_two_series():
    df = _make_ohlcv()
    k, d = compute_stochastic(df)
    assert len(k) == len(df)
    assert len(d) == len(df)


def test_stochastic_bounded_0_100():
    df = _make_ohlcv()
    k, d = compute_stochastic(df)
    k_valid, d_valid = k.dropna(), d.dropna()
    assert k_valid.between(-0.01, 100.01).all()
    assert d_valid.between(-0.01, 100.01).all()


def test_stochastic_summary_structure():
    df = _make_ohlcv()
    summary = stochastic_summary(df)
    assert summary is not None
    assert set(summary.keys()) == {"k", "d", "signal", "crossed"}
    assert summary["signal"] in ("wyprzedanie", "przegrzanie", "neutralnie")


def test_stochastic_summary_none_on_empty():
    assert stochastic_summary(pd.DataFrame()) is None


def test_stochastic_signal_overbought_at_top_of_range():
    # Cena rośnie monotonicznie do nowego maksimum -> blisko top zakresu.
    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(100, 150, n)
    df = pd.DataFrame(
        {"High": close + 0.5, "Low": close - 0.5, "Close": close,
         "Volume": np.full(n, 1_000_000.0)},
        index=idx,
    )
    summary = stochastic_summary(df, k_window=14, d_window=3)
    assert summary["signal"] == "przegrzanie"


def test_stochastic_signal_oversold_at_bottom_of_range():
    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(150, 100, n)
    df = pd.DataFrame(
        {"High": close + 0.5, "Low": close - 0.5, "Close": close,
         "Volume": np.full(n, 1_000_000.0)},
        index=idx,
    )
    summary = stochastic_summary(df, k_window=14, d_window=3)
    assert summary["signal"] == "wyprzedanie"


# ----------------------------------------------------------------------
# OBV i dywergencja
# ----------------------------------------------------------------------
def test_compute_obv_returns_series():
    df = _make_ohlcv()
    obv = compute_obv(df)
    assert len(obv) == len(df)


def test_obv_missing_volume_returns_empty():
    df = pd.DataFrame({"Close": [1, 2, 3]})
    obv = compute_obv(df)
    assert obv.empty or obv.isna().all()


def test_obv_increases_on_up_day():
    idx = pd.date_range("2024-01-01", periods=3, freq="B")
    df = pd.DataFrame(
        {"Close": [100.0, 105.0, 103.0], "Volume": [1000.0, 2000.0, 1500.0]},
        index=idx,
    )
    obv = compute_obv(df)
    # dzień 2: cena w górę -> OBV rośnie o wolumen dnia 2
    assert obv.iloc[1] == obv.iloc[0] + 2000.0
    # dzień 3: cena w dół -> OBV maleje o wolumen dnia 3
    assert obv.iloc[2] == obv.iloc[1] - 1500.0


def test_detect_obv_divergence_bearish_constructed():
    """Cena robi nowe maksimum, ale wolumen na wzroście maleje -> bearish."""
    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.concatenate([np.linspace(100, 90, 20), np.linspace(90, 110, 10)])
    volume = np.full(n, 1_000_000.0)
    volume[20:] = np.linspace(1_000_000, 100_000, 10)  # malejący wolumen na wzroście
    df = pd.DataFrame(
        {"High": close + 0.5, "Low": close - 0.5, "Close": close, "Volume": volume},
        index=idx,
    )
    divergence = detect_obv_divergence(df, window=20)
    assert divergence is not None
    assert divergence["type"] == "bearish"


def test_detect_obv_divergence_none_on_insufficient_data():
    df = _make_ohlcv(n=5)
    assert detect_obv_divergence(df, window=20) is None


def test_detect_obv_divergence_none_when_confirmed():
    """Cena i wolumen rosną razem - brak dywergencji."""
    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(100, 130, n)
    volume = np.linspace(1_000_000, 3_000_000, n)  # wolumen rośnie razem z ceną
    df = pd.DataFrame(
        {"High": close + 0.5, "Low": close - 0.5, "Close": close, "Volume": volume},
        index=idx,
    )
    divergence = detect_obv_divergence(df, window=20)
    assert divergence is None


# ----------------------------------------------------------------------
# WSPARCIE I OPÓR
# ----------------------------------------------------------------------
def test_detect_support_resistance_structure():
    df = _make_ohlcv(n=150)
    levels = detect_support_resistance(df)
    assert "support" in levels and "resistance" in levels
    assert isinstance(levels["support"], list)
    assert isinstance(levels["resistance"], list)


def test_detect_support_resistance_empty_on_no_data():
    levels = detect_support_resistance(pd.DataFrame())
    assert levels == {"support": [], "resistance": []}


def test_detect_support_resistance_empty_on_insufficient_data():
    df = _make_ohlcv(n=5)
    levels = detect_support_resistance(df, window=10)
    assert levels == {"support": [], "resistance": []}


def test_detect_support_resistance_respects_max_levels():
    df = _make_ohlcv(n=150, seed=7, vol=0.03)
    levels = detect_support_resistance(df, max_levels=3)
    assert len(levels["support"]) <= 3
    assert len(levels["resistance"]) <= 3


def test_detect_support_resistance_levels_sorted_ascending():
    df = _make_ohlcv(n=150, seed=3, vol=0.025)
    levels = detect_support_resistance(df)
    assert levels["support"] == sorted(levels["support"])
    assert levels["resistance"] == sorted(levels["resistance"])


def test_detect_support_resistance_clusters_nearby_levels():
    """Sztuczne dane z dwoma bliskimi minimami - powinny się zgrupować."""
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    # Wzorzec V-V z dwoma blisko leżącymi dołkami (~1% różnicy)
    close = np.concatenate([
        np.linspace(110, 100, 15), np.linspace(100, 108, 10),
        np.linspace(108, 100.5, 15), np.linspace(100.5, 112, 20),
    ])
    df = pd.DataFrame(
        {"High": close + 0.3, "Low": close - 0.3, "Close": close},
        index=idx,
    )
    levels = detect_support_resistance(df, window=5, lookback=60)
    # Dwa blisko leżące dołki (100 i 100.5, ~0.5% różnicy) powinny dać
    # mniej poziomów wsparcia niż gdyby się nie zgrupowały.
    assert len(levels["support"]) <= 2
