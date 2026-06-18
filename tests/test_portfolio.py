"""
Testy dla portfolio.py
========================
Używają `fake_yfinance` (offline, deterministyczne dane) i izolowanej
bazy danych (`isolated_db`).
"""

import portfolio
import stock_analyzer as sa


def test_analyze_portfolio_empty(isolated_db):
    result = portfolio.analyze_portfolio("alice", sa.analyze_ticker)
    assert result["positions"] == []
    assert result["totals"] is None
    assert result["allocation_by_sector"] == {}
    assert result["warnings"] == []


def test_analyze_portfolio_with_positions(isolated_db, fake_yfinance):
    db = isolated_db
    db.add_position("alice", "AAPL", 5, 100.0, "2024-01-01", "core position")
    db.add_position("alice", "MSFT", 2, 100.0, "2024-02-01")

    result = portfolio.analyze_portfolio("alice", sa.analyze_ticker)

    assert len(result["positions"]) == 2
    assert result["totals"] is not None
    assert result["totals"]["total_cost"] == 5 * 100.0 + 2 * 100.0

    for p in result["positions"]:
        assert p["current_value"] == round(p["shares"] * p["current_price"], 2)
        assert 0 <= p["score"] <= 100

    # obie pozycje to "Technology" (FakeTicker) -> 100% jednego sektora
    assert result["allocation_by_sector"].get("Technology") == 100.0
    assert any("Sektor" in w for w in result["warnings"])


def test_analyze_portfolio_single_position_warning(isolated_db, fake_yfinance):
    db = isolated_db
    db.add_position("alice", "AAPL", 1, 100.0, "2024-01-01")

    result = portfolio.analyze_portfolio("alice", sa.analyze_ticker)
    assert any("jednej spółki" in w for w in result["warnings"])


def test_analyze_portfolio_handles_errors(isolated_db, fake_yfinance):
    db = isolated_db
    db.add_position("alice", "AAPL", 1, 100.0, "2024-01-01")

    def failing_analyze(ticker):
        return {"ticker": ticker, "error": "boom"}

    result = portfolio.analyze_portfolio("alice", failing_analyze)
    assert result["positions"] == []
    assert "AAPL" in result["errors"]


# ----------------------------------------------------------------------
# Korelacja
# ----------------------------------------------------------------------
def test_correlation_matrix_basic(fake_yfinance):
    result = portfolio.compute_correlation_matrix(["AAPL", "MSFT", "GOOGL"], period="6mo")

    assert result["matrix"] is not None
    assert result["matrix"].shape == (3, 3)
    # diagonalna korelacji z samym sobą = 1
    for t in ["AAPL", "MSFT", "GOOGL"]:
        assert abs(result["matrix"].loc[t, t] - 1.0) < 1e-9
    assert result["errors"] == []


def test_correlation_matrix_too_few_tickers(fake_yfinance):
    result = portfolio.compute_correlation_matrix(["AAPL"], period="6mo")
    assert result["matrix"] is None
    assert result["high_pairs"] == []


def test_correlation_matrix_high_pairs_detection(fake_yfinance, monkeypatch):
    """Jeśli dwa tickery mają identyczne ceny, korelacja powinna być ~1.0
    i znaleźć się w high_pairs."""
    import pandas as pd
    import numpy as np

    class IdenticalTicker(fake_yfinance):
        def history(self, period=None, interval=None):
            rng = np.random.default_rng(123)  # ten sam seed dla obu tickerow
            n = 200
            dates = pd.date_range("2024-01-01", periods=n, freq="B")
            returns = rng.normal(0.0003, 0.015, size=n)
            prices = 100 * np.cumprod(1 + returns)
            return pd.DataFrame({"Close": prices, "Volume": [1000] * n}, index=dates)

    monkeypatch.setattr(portfolio.yf, "Ticker", IdenticalTicker)

    result = portfolio.compute_correlation_matrix(["AAA", "BBB"], period="6mo")
    assert result["matrix"].loc["AAA", "BBB"] > 0.99
    assert len(result["high_pairs"]) == 1
    a, b, corr = result["high_pairs"][0]
    assert {a, b} == {"AAA", "BBB"}
    assert corr > 0.75
