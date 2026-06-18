"""
Konfiguracja testów (pytest)
==============================
- `isolated_db`: każdy test dostaje czystą, tymczasową bazę SQLite
  (zamiast prawdziwej `stock_app.db`), więc testy nie wpływają na
  realne dane użytkownika i mogą działać równolegle.
- `fake_yfinance`: podstawia w `stock_analyzer` i `portfolio` fałszywą
  klasę `yf.Ticker`, która generuje deterministyczne, syntetyczne dane
  - testy działają OFFLINE, bez zapytań do Yahoo Finance.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest


class FakeTicker:
    """Podstawowy zamiennik yfinance.Ticker z deterministycznymi danymi."""

    def __init__(self, ticker):
        self.ticker = ticker
        self._seed = abs(hash(ticker)) % 10_000

    @property
    def info(self) -> dict:
        return {
            "currency": "USD",
            "longName": f"{self.ticker} Inc.",
            "sector": "Technology",
            "industry": "Software",
            "trailingPE": 28.0,
            "forwardPE": 24.0,
            "pegRatio": 1.2,
            "dividendYield": 0.012,
            "payoutRatio": 0.3,
            "debtToEquity": 45.0,
            "revenueGrowth": 0.15,
            "earningsGrowth": 0.10,
            "freeCashflow": 5_000_000_000,
            "totalDebt": 10_000_000_000,
            "totalCash": 8_000_000_000,
            "grossMargins": 0.4,
            "operatingMargins": 0.2,
            "profitMargins": 0.15,
            "returnOnEquity": 0.2,
            "currentRatio": 1.5,
            "quickRatio": 1.2,
        }

    @property
    def news(self) -> list:
        return [
            {
                "title": "Company posts record profit and strong growth",
                "link": "https://example.com/news/1",
                "publisher": "Reuters",
                "providerPublishTime": 1_700_000_000,
            },
            {
                "content": {
                    "title": "Analysts upgrade stock after rally",
                    "canonicalUrl": {"url": "https://example.com/news/2"},
                    "provider": {"displayName": "Bloomberg"},
                    "pubDate": "2024-02-01T10:00:00Z",
                }
            },
        ]

    @property
    def dividends(self) -> pd.Series:
        return pd.Series(
            [1.0, 1.1],
            index=pd.to_datetime(["2023-06-01", "2023-12-01"]),
        )

    @property
    def calendar(self) -> dict:
        return {
            "Earnings Date": [pd.Timestamp("2026-08-01")],
            "Ex-Dividend Date": pd.Timestamp("2026-07-15"),
        }

    def history(self, period=None, interval=None) -> pd.DataFrame:
        n = 1300  # ~5 lat danych dziennych - wystarczy na backtest/walk-forward
        rng = np.random.default_rng(self._seed)
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        # losowy spacer + lekki trend wzrostowy, żeby dane były "realistyczne"
        returns = rng.normal(loc=0.0003, scale=0.015, size=n)
        close = 100 * np.cumprod(1 + returns)
        volume = rng.integers(1_000, 5_000, size=n)
        # OHLC wyprowadzone z ceny zamknięcia (do wykresów świecowych)
        return pd.DataFrame({
            "Open": close * (1 + rng.normal(0, 0.003, n)),
            "High": close * (1 + np.abs(rng.normal(0, 0.008, n))),
            "Low":  close * (1 - np.abs(rng.normal(0, 0.008, n))),
            "Close": close,
            "Volume": volume,
        }, index=dates)


@pytest.fixture
def fake_yfinance(monkeypatch):
    """Podstawia FakeTicker we wszystkich modułach, które importują yfinance."""
    import stock_analyzer
    import portfolio

    monkeypatch.setattr(stock_analyzer.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(portfolio.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(stock_analyzer.yf, "Search", FakeSearch, raising=False)
    return FakeTicker


class FakeSearch:
    """Zamiennik yfinance.Search – zwraca deterministyczne wyniki wyszukiwania."""

    def __init__(self, query, max_results=8):
        q = (query or "").lower()
        if "apple" in q or "aapl" in q:
            self.quotes = [
                {"symbol": "AAPL", "longname": "Apple Inc.",
                 "exchange": "NMS", "quoteType": "EQUITY"},
                {"symbol": "APLE", "shortname": "Apple Hospitality REIT",
                 "exchange": "NYQ", "quoteType": "EQUITY"},
            ][:max_results]
        else:
            self.quotes = []


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Każdy test dostaje świeżą, tymczasową bazę SQLite."""
    import database as db

    test_db_path = str(tmp_path / "test_stock_app.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    yield db
