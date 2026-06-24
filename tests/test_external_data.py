"""
Testy dla external_data.py
=============================
Sprawdzają klientów Binance / CoinGecko / Alpaca z zamockowanym
requests.get (bez prawdziwych połączeń sieciowych) oraz poprawną
degradację przy błędach sieci / braku konfiguracji.
"""
import os

import requests

import external_data as ed


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data


# ----------------------------------------------------------------------
# BINANCE
# ----------------------------------------------------------------------
def test_binance_symbol_for_known_ticker():
    assert ed.binance_symbol_for("BTC-USD") == "BTCUSDT"
    assert ed.binance_symbol_for("eth-usd") == "ETHUSDT"  # case-insensitive


def test_binance_symbol_for_unknown_ticker():
    assert ed.binance_symbol_for("AAPL") is None
    assert ed.binance_symbol_for("DOGE-USD") is None  # spoza naszej listy


def test_is_binance_supported():
    assert ed.is_binance_supported("BTC-USD") is True
    assert ed.is_binance_supported("AAPL") is False


def test_get_binance_price_success(monkeypatch):
    def fake_get(url, params=None, timeout=None, headers=None):
        assert "ticker/24hr" in url
        assert params["symbol"] == "BTCUSDT"
        return _FakeResponse({
            "lastPrice": "67000.50", "priceChangePercent": "2.5",
            "volume": "12345.6", "highPrice": "68000", "lowPrice": "65000",
        })

    monkeypatch.setattr(requests, "get", fake_get)
    result = ed.get_binance_price("BTC-USD")
    assert result is not None
    assert result["price"] == 67000.5
    assert result["change_24h_pct"] == 2.5
    assert result["source"] == "Binance (live)"


def test_get_binance_price_unsupported_ticker_returns_none(monkeypatch):
    def fake_get(*a, **k):
        raise AssertionError("nie powinno wołać API dla nieobsługiwanego tickera")

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_binance_price("AAPL") is None


def test_get_binance_price_http_error_returns_none(monkeypatch):
    def fake_get(*a, **k):
        return _FakeResponse({}, status_code=500)

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_binance_price("BTC-USD") is None


def test_get_binance_price_network_error_returns_none(monkeypatch):
    def fake_get(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_binance_price("BTC-USD") is None


def test_get_binance_price_malformed_response_returns_none(monkeypatch):
    def fake_get(*a, **k):
        return _FakeResponse({"unexpected": "format"})

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_binance_price("BTC-USD") is None


def test_get_binance_klines_success(monkeypatch):
    def fake_get(url, params=None, timeout=None, headers=None):
        assert "klines" in url
        return _FakeResponse([[1700000000000, "67000", "68000", "66000", "67500", "100"]] * 5)

    monkeypatch.setattr(requests, "get", fake_get)
    klines = ed.get_binance_klines("ETH-USD")
    assert klines is not None
    assert len(klines) == 5


def test_get_binance_klines_unsupported_ticker():
    assert ed.get_binance_klines("AAPL") is None


# ----------------------------------------------------------------------
# COINGECKO
# ----------------------------------------------------------------------
def test_get_btc_dominance_success(monkeypatch):
    def fake_get(url, params=None, timeout=None, headers=None):
        assert "coingecko.com" in url
        return _FakeResponse({
            "data": {
                "market_cap_percentage": {"btc": 54.3, "eth": 17.1},
                "total_market_cap": {"usd": 2.5e12},
                "market_cap_change_percentage_24h_usd": 1.2,
            }
        })

    monkeypatch.setattr(requests, "get", fake_get)
    result = ed.get_btc_dominance()
    assert result is not None
    assert result["btc_dominance_pct"] == 54.3
    assert result["eth_dominance_pct"] == 17.1


def test_get_btc_dominance_network_error_returns_none(monkeypatch):
    def fake_get(*a, **k):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_btc_dominance() is None


def test_get_btc_dominance_malformed_response_returns_none(monkeypatch):
    def fake_get(*a, **k):
        return _FakeResponse({"no_data_key": True})

    monkeypatch.setattr(requests, "get", fake_get)
    assert ed.get_btc_dominance() is None


# ----------------------------------------------------------------------
# ALPACA
# ----------------------------------------------------------------------
def test_is_alpaca_configured_false_without_keys(monkeypatch):
    monkeypatch.setattr(os.environ, "get", lambda k, d=None: None)
    # Bezpośrednio przez os.environ (prościej niż mockować cały moduł)
    saved = {}
    for key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        assert ed.is_alpaca_configured() is False
    finally:
        os.environ.update(saved)


def test_is_alpaca_configured_true_with_env_keys(monkeypatch):
    monkeypatch.setattr(os.environ, "setdefault", os.environ.setdefault)
    os.environ["ALPACA_API_KEY"] = "test-key"
    os.environ["ALPACA_SECRET_KEY"] = "test-secret"
    try:
        assert ed.is_alpaca_configured() is True
    finally:
        del os.environ["ALPACA_API_KEY"]
        del os.environ["ALPACA_SECRET_KEY"]


def test_is_alpaca_supported_us_ticker():
    assert ed.is_alpaca_supported("AAPL") is True
    assert ed.is_alpaca_supported("TSLA") is True


def test_is_alpaca_supported_excludes_non_us_formats():
    assert ed.is_alpaca_supported("CDR.WA") is False    # GPW
    assert ed.is_alpaca_supported("SAP.DE") is False    # Niemcy
    assert ed.is_alpaca_supported("BTC-USD") is False   # krypto
    assert ed.is_alpaca_supported("TOOLONGTICKER") is False


def test_get_alpaca_quote_without_credentials_returns_none():
    saved = {}
    for key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        assert ed.get_alpaca_quote("AAPL") is None
    finally:
        os.environ.update(saved)


def test_get_alpaca_quote_success(monkeypatch):
    os.environ["ALPACA_API_KEY"] = "test-key"
    os.environ["ALPACA_SECRET_KEY"] = "test-secret"

    def fake_get(url, params=None, timeout=None, headers=None):
        assert headers["APCA-API-KEY-ID"] == "test-key"
        return _FakeResponse({"quote": {"bp": 189.5, "ap": 189.6, "t": "2026-06-20T10:00:00Z"}})

    monkeypatch.setattr(requests, "get", fake_get)
    try:
        result = ed.get_alpaca_quote("AAPL")
        assert result is not None
        assert result["price"] == 189.55
        assert result["source"] == "Alpaca (live)"
    finally:
        del os.environ["ALPACA_API_KEY"]
        del os.environ["ALPACA_SECRET_KEY"]


def test_get_alpaca_quote_invalid_ticker_format_returns_none():
    os.environ["ALPACA_API_KEY"] = "test-key"
    os.environ["ALPACA_SECRET_KEY"] = "test-secret"
    try:
        assert ed.get_alpaca_quote("CDR.WA") is None
    finally:
        del os.environ["ALPACA_API_KEY"]
        del os.environ["ALPACA_SECRET_KEY"]
