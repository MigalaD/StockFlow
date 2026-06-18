"""
Testy dla backtest.py
=======================
Używają `fake_yfinance` (offline, ~5 lat syntetycznych danych dziennych),
żeby przetestować backtest, heatmapę progów i analizę walk-forward bez
połączenia z Yahoo Finance.
"""

import backtest as bt


def test_backtest_basic_structure(fake_yfinance):
    result = bt.backtest_score_strategy("AAPL", period="2y", buy_threshold=60, sell_threshold=40)

    assert "error" not in result
    assert {"equity_curve", "trades", "metrics"} <= set(result.keys())

    metrics = result["metrics"]
    for key in ("total_return", "buyhold_return", "num_trades", "win_rate",
                "max_drawdown", "final_value", "buyhold_final_value",
                "still_open", "sharpe", "sortino"):
        assert key in metrics

    equity = result["equity_curve"]
    assert list(equity.columns) == ["Date", "Strategy", "BuyHold"]
    assert len(equity) > 0
    # kapital startowy powinien byc widoczny na poczatku obu krzywych
    assert equity["Strategy"].iloc[0] == 10_000
    assert equity["BuyHold"].iloc[0] == 10_000


def test_backtest_invalid_thresholds_still_runs(fake_yfinance):
    # buy <= sell jest sprawdzane w UI, ale modul sam nie powinien sie wywalic
    result = bt.backtest_score_strategy("AAPL", period="1y", buy_threshold=40, sell_threshold=60)
    assert "error" not in result


def test_backtest_custom_capital(fake_yfinance):
    result = bt.backtest_score_strategy("AAPL", period="2y", initial_capital=5_000)
    assert result["equity_curve"]["Strategy"].iloc[0] == 5_000
    assert result["equity_curve"]["BuyHold"].iloc[0] == 5_000


# ----------------------------------------------------------------------
# Heatmapa progów
# ----------------------------------------------------------------------
def test_run_threshold_grid(fake_yfinance):
    result = bt.run_threshold_grid(
        "AAPL", period="2y",
        buy_range=range(50, 81, 10), sell_range=range(20, 51, 10),
    )

    assert "error" not in result
    assert result["grid"] is not None
    assert "best" in result and {"buy", "sell", "return"} <= set(result["best"].keys())
    assert isinstance(result["buyhold_return"], float)

    # best powinien byc faktycznie najwiekszy w gridzie
    max_in_grid = result["grid"].max().max()
    assert result["best"]["return"] <= max_in_grid + 1e-9


# ----------------------------------------------------------------------
# Walk-forward
# ----------------------------------------------------------------------
def test_walk_forward_analysis(fake_yfinance):
    result = bt.walk_forward_analysis("AAPL", period="5y", n_windows=4)

    assert "error" not in result
    assert "windows" in result and "summary" in result
    assert len(result["windows"]) == 4

    for w in result["windows"]:
        for key in ("okres_od", "okres_do", "strategia_%", "kup_i_trzymaj_%",
                     "lepsza_niz_bh", "liczba_transakcji", "max_obsuniecie_%"):
            assert key in w

    summary = result["summary"]
    assert summary["n_windows"] == 4
    assert 0 <= summary["wins"] <= 4
    assert 0 <= summary["win_rate_pct"] <= 100


def test_walk_forward_too_many_windows(fake_yfinance):
    # FakeTicker zwraca ~1300 dni (po dropna ~1100) - 100 okien to zbyt wiele
    result = bt.walk_forward_analysis("AAPL", period="5y", n_windows=100)
    assert "error" in result
