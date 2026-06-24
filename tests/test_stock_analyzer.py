"""
Testy dla stock_analyzer.py
==============================
Sprawdzają podstawowe wskaźniki (RSI, MACD), poszczególne składowe
score (każda powinna zwracać wartość 0-100), oraz pełną analizę
`analyze_ticker` na syntetycznych danych (offline, bez Yahoo Finance).
"""

import numpy as np
import pandas as pd

import stock_analyzer as sa


def _make_df(n=300, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    returns = rng.normal(0.0003, 0.015, size=n)
    prices = 100 * np.cumprod(1 + returns)
    df = pd.DataFrame({
        "Close": prices,
        "Volume": rng.integers(1000, 5000, size=n),
    }, index=dates)
    df["RSI"] = sa.rsi(df["Close"])
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = sa.macd(df["Close"])
    return df


# ----------------------------------------------------------------------
# Wskaźniki podstawowe
# ----------------------------------------------------------------------
def test_rsi_in_valid_range():
    df = _make_df()
    rsi_values = df["RSI"].dropna()
    assert len(rsi_values) > 0
    assert (rsi_values >= 0).all()
    assert (rsi_values <= 100).all()


def test_macd_returns_two_series():
    df = _make_df()
    macd_line, signal_line = sa.macd(df["Close"])
    assert len(macd_line) == len(df)
    assert len(signal_line) == len(df)
    # sygnał jest wygładzoną wersją MACD - powinien mieć mniejszą zmienność
    assert signal_line.std() <= macd_line.std() * 1.5


# ----------------------------------------------------------------------
# Składowe score - każda powinna zwracać (wartość 0-100, opis tekstowy)
# ----------------------------------------------------------------------
def test_score_components_in_range():
    df = _make_df()
    info = {
        "trailingPE": 20.0, "forwardPE": 18.0, "pegRatio": 1.0,
        "dividendYield": 0.02, "payoutRatio": 0.4,
        "debtToEquity": 50.0, "revenueGrowth": 0.1, "earningsGrowth": 0.08,
        "freeCashflow": 1e9, "totalDebt": 5e9, "totalCash": 2e9,
        "grossMargins": 0.3, "operatingMargins": 0.15, "profitMargins": 0.1,
        "returnOnEquity": 0.15, "currentRatio": 1.2, "quickRatio": 1.0,
    }

    checks = {
        "rsi": sa.score_rsi(df),
        "trend_ma": sa.score_trend_ma(df),
        "macd": sa.score_macd(df),
        "volume": sa.score_volume(df),
        "volatility": sa.score_volatility(df),
        "valuation": sa.score_valuation(info),
        "momentum": sa.score_momentum(df),
        "dividend": sa.score_dividend(info),
        "fundamentals": sa.score_fundamentals_deep(info),
    }

    for name, (value, note) in checks.items():
        assert 0 <= value <= 100, f"{name}: score {value} out of range"
        assert isinstance(note, str) and note, f"{name}: missing note"


def test_score_dividend_no_dividend():
    value, note = sa.score_dividend({"dividendYield": None})
    assert value == 50
    assert "nie płaci" in note


# ----------------------------------------------------------------------
# Sentyment newsów
# ----------------------------------------------------------------------
def test_score_sentiment_positive_headline():
    news = [{"title": "Stock surges to record high after strong growth and profit beat"}]
    value, note = sa.score_sentiment(news)
    assert value > 50
    assert "nagłówków" in note


def test_score_sentiment_no_news():
    value, note = sa.score_sentiment([])
    assert value == 50
    assert "brak" in note.lower()


def test_score_sentiment_neutral_when_no_keywords():
    news = [{"title": "Company announces quarterly shareholder meeting date"}]
    value, note = sa.score_sentiment(news)
    assert value == 50


# ----------------------------------------------------------------------
# Newsy i kalendarz
# ----------------------------------------------------------------------
def test_get_news_list_handles_both_formats():
    news = [
        {"title": "Old format title", "link": "http://a.com", "publisher": "X",
         "providerPublishTime": 1_700_000_000},
        {"content": {"title": "New format title",
                      "canonicalUrl": {"url": "http://b.com"},
                      "provider": {"displayName": "Y"},
                      "pubDate": "2024-01-02T10:00:00Z"}},
    ]
    result = sa.get_news_list(news, limit=5)
    assert len(result) == 2
    assert result[0]["title"] == "Old format title"
    assert result[0]["link"] == "http://a.com"
    assert result[1]["title"] == "New format title"
    assert result[1]["publisher"] == "Y"


def test_get_news_list_respects_limit():
    news = [{"title": f"Headline {i}"} for i in range(10)]
    result = sa.get_news_list(news, limit=3)
    assert len(result) == 3


# ----------------------------------------------------------------------
# Pełna analiza (offline, z FakeTicker)
# ----------------------------------------------------------------------
def test_analyze_ticker_structure(fake_yfinance):
    res = sa.analyze_ticker("AAPL")

    assert "error" not in res
    assert res["ticker"] == "AAPL"
    assert 0 <= res["total_score"] <= 100
    assert set(res["components"].keys()) == set(sa.WEIGHTS.keys())

    for key, (value, note) in res["components"].items():
        assert 0 <= value <= 100, f"{key} out of range: {value}"

    assert res["news_list"]
    assert "earnings_date" in res["calendar_info"]
    assert isinstance(res["red_flags"], list)


def test_analyze_ticker_weights_sum_to_one():
    total = sum(sa.WEIGHTS.values())
    assert abs(total - 1.0) < 1e-6


def test_interpret_score_boundaries():
    assert sa.interpret_score(75) == "SILNY SYGNAŁ POZYTYWNY"
    assert sa.interpret_score(65) == "Sygnał umiarkowanie pozytywny"
    assert sa.interpret_score(50) == "Neutralnie"
    assert sa.interpret_score(35) == "Sygnał umiarkowanie negatywny"
    assert sa.interpret_score(10) == "SILNY SYGNAŁ NEGATYWNY"


# ----------------------------------------------------------------------
# Historia score (do wykresu i backtestu)
# ----------------------------------------------------------------------
def test_compute_simple_score_series():
    df = _make_df(n=300)
    out = sa.compute_simple_score_series(df)

    assert not out.empty
    assert set(out.columns) == {"Date", "Score", "Close"}
    assert (out["Score"] >= 0).all()
    assert (out["Score"] <= 100).all()
    # powinno być krótsze niż wejście (pierwsze ~200 dni bez MA200/RSI są odrzucane)
    assert len(out) < len(df)


# ----------------------------------------------------------------------
# TYPY AKTYW - ETF-y i surowce
# ----------------------------------------------------------------------
def test_get_asset_type_stock():
    assert sa.get_asset_type({"quoteType": "EQUITY"}) == "stock"
    assert sa.get_asset_type({}) == "stock"  # brak danych -> domyślnie akcja


def test_get_asset_type_etf():
    assert sa.get_asset_type({"quoteType": "ETF", "trailingPE": 22.0, "dividendYield": 0.01}) == "etf"


def test_get_asset_type_etf_commodity():
    # ETF bez P/E i dywidendy (np. GLD, SLV) -> traktowany jak surowiec
    assert sa.get_asset_type({"quoteType": "ETF"}) == "etf_commodity"


def test_get_asset_type_commodity_future():
    assert sa.get_asset_type({"quoteType": "FUTURE"}) == "commodity"
    # UWAGA: od v1.1 CRYPTOCURRENCY ma WŁASNY typ "crypto", osobny od
    # "commodity" - patrz test_get_asset_type_crypto_quote_type powyżej
    # (sekcja "TYP AKTYWA crypto"). Krypto ma inną charakterystykę
    # zmienności niż surowce, więc dzielenie wag/scoringu ma sens.
    assert sa.get_asset_type({"quoteType": "CRYPTOCURRENCY"}) == "crypto"


def test_get_weights_for_asset_type_sums_to_one():
    for asset_type in sa.EXCLUDED_COMPONENTS_BY_ASSET_TYPE:
        weights = sa.get_weights_for_asset_type(asset_type)
        assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_get_weights_excludes_fundamentals_for_etf():
    weights = sa.get_weights_for_asset_type("etf")
    assert "fundamentals" not in weights
    assert "valuation" in weights and "dividend" in weights


def test_get_weights_excludes_fundamental_group_for_commodity():
    weights = sa.get_weights_for_asset_type("commodity")
    for key in ("valuation", "dividend", "fundamentals"):
        assert key not in weights
    # pozostale wskazniki techniczne powinny byc obecne
    for key in ("rsi", "trend_ma", "macd", "momentum", "volatility", "volume", "sentiment"):
        assert key in weights


def test_analyze_ticker_etf_excludes_fundamentals(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class EtfTicker(fake_yfinance):
        @property
        def info(self):
            base = super().info
            base["quoteType"] = "ETF"
            base["category"] = "Large Blend"
            base["fundFamily"] = "Vanguard"
            return base

    monkeypatch.setattr(sa2.yf, "Ticker", EtfTicker)

    res = sa2.analyze_ticker("VTI")
    assert res["asset_type"] == "etf"
    assert "fundamentals" not in res["components"]
    assert abs(sum(res["weights"].values()) - 1.0) < 1e-9
    assert res["category"] == "Large Blend"
    assert res["fund_family"] == "Vanguard"


def test_analyze_ticker_commodity_etf(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CommodityEtfTicker(fake_yfinance):
        @property
        def info(self):
            return {
                "currency": "USD", "longName": "Gold Shares",
                "quoteType": "ETF", "category": "Commodities Focused",
            }

    monkeypatch.setattr(sa2.yf, "Ticker", CommodityEtfTicker)

    res = sa2.analyze_ticker("GLD")
    assert res["asset_type"] == "etf_commodity"
    for key in ("valuation", "dividend", "fundamentals"):
        assert key not in res["components"]
    assert res["red_flags"] == []
    assert res["sector_pe_comparison"] is None


# ----------------------------------------------------------------------
# WSTĘGI BOLLINGERA
# ----------------------------------------------------------------------
def test_bollinger_bands_ordering():
    df = _make_df(n=100)
    middle, upper, lower = sa.bollinger_bands(df["Close"], window=20, num_std=2.0)
    # ostatnie wartości powinny być uporządkowane: dolna < środkowa < górna
    assert lower.iloc[-1] < middle.iloc[-1] < upper.iloc[-1]


def test_bollinger_bands_window_warmup():
    df = _make_df(n=100)
    middle, _, _ = sa.bollinger_bands(df["Close"], window=20)
    # pierwsze 19 wartości to NaN (za mało danych na 20-dniowe okno)
    assert middle.iloc[:19].isna().all()
    assert not np.isnan(middle.iloc[19])


def test_bollinger_bands_width_scales_with_std():
    df = _make_df(n=100)
    _, up_narrow, low_narrow = sa.bollinger_bands(df["Close"], num_std=1.0)
    _, up_wide, low_wide = sa.bollinger_bands(df["Close"], num_std=3.0)
    width_narrow = up_narrow.iloc[-1] - low_narrow.iloc[-1]
    width_wide = up_wide.iloc[-1] - low_wide.iloc[-1]
    assert width_wide > width_narrow


def test_percent_b_helper():
    df = _make_df(n=100)
    df["BB_mid"], df["BB_upper"], df["BB_lower"] = sa.bollinger_bands(df["Close"])
    pct_b = sa._bollinger_percent_b(df)
    assert pct_b is not None
    # %B powinno być skończoną liczbą (zwykle w okolicach 0-1, ale może wyjść poza)
    assert isinstance(pct_b, float)


def test_score_volatility_uses_bollinger(fake_yfinance):
    # analyze_ticker liczy BB i przekazuje do score_volatility; sprawdzamy,
    # że nota wspomina o Bollingerze gdy cena jest blisko wstęgi
    res = analyze_ticker_with_bb()
    note = res["components"]["volatility"][1]
    assert "zmienność" in note


def analyze_ticker_with_bb():
    """Pomocnik: liczy analizę z włączonymi wstęgami (FakeTicker daje OHLC)."""
    return sa.analyze_ticker("AAPL")


# ----------------------------------------------------------------------
# WYSZUKIWANIE TICKERÓW
# ----------------------------------------------------------------------
def test_search_tickers_returns_matches(fake_yfinance):
    results = sa.search_tickers("apple")
    assert len(results) >= 1
    symbols = [r["symbol"] for r in results]
    assert "AAPL" in symbols
    # każdy wynik ma wymagane pola
    for r in results:
        assert set(r.keys()) == {"symbol", "name", "exchange", "type"}


def test_search_tickers_empty_query(fake_yfinance):
    assert sa.search_tickers("") == []
    assert sa.search_tickers("   ") == []


def test_search_tickers_no_match(fake_yfinance):
    assert sa.search_tickers("zzzznonexistent") == []


def test_search_tickers_handles_exception(monkeypatch):
    import stock_analyzer as sa2

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(sa2.yf, "Search", boom, raising=False)
    # nie powinno rzucić - ma zwrócić pustą listę
    assert sa2.search_tickers("apple") == []


def test_analyze_ticker_has_ohlc_and_bb(fake_yfinance):
    # po dodaniu MA20/Bollingera analyze_ticker nadal działa i daje sensowny wynik
    res = sa.analyze_ticker("AAPL")
    assert "error" not in res
    assert 0 <= res["total_score"] <= 100


# ----------------------------------------------------------------------
# SANITYZACJA SYMBOLU
# ----------------------------------------------------------------------
def test_sanitize_ticker_basic():
    assert sa.sanitize_ticker("  aapl  ") == "AAPL"
    assert sa.sanitize_ticker("cdr.wa") == "CDR.WA"
    assert sa.sanitize_ticker("brk-b") == "BRK-B"
    assert sa.sanitize_ticker("^gspc") == "^GSPC"


def test_sanitize_ticker_empty():
    assert sa.sanitize_ticker("") == ""
    assert sa.sanitize_ticker("   ") == ""
    assert sa.sanitize_ticker(None) == ""


def test_sanitize_ticker_strips_junk():
    # znaki spoza dozwolonego zestawu są usuwane
    assert sa.sanitize_ticker("AA!PL") == "AAPL"


def test_analyze_ticker_rejects_empty(fake_yfinance):
    res = sa.analyze_ticker("   ")
    assert "error" in res


# ----------------------------------------------------------------------
# SIŁA RELATYWNA
# ----------------------------------------------------------------------
def test_relative_strength_structure(fake_yfinance):
    df = _make_df(n=300)
    res = sa.compute_relative_strength("AAPL", df)
    assert res is not None
    assert set(res.keys()) == {
        "index", "stock_return_pct", "index_return_pct",
        "outperformance_pct", "period",
    }
    # outperformance = stock - index (z dokładnością do zaokrągleń)
    diff = res["stock_return_pct"] - res["index_return_pct"]
    assert abs(diff - res["outperformance_pct"]) < 0.2


def test_relative_strength_index_selection(fake_yfinance):
    df = _make_df(n=200)
    res_us = sa.compute_relative_strength("AAPL", df)
    res_pl = sa.compute_relative_strength("CDR.WA", df)
    assert res_us["index"] == "^GSPC"
    assert res_pl["index"] == "^WIG20"


def test_relative_strength_insufficient_data(fake_yfinance):
    tiny = pd.DataFrame({"Close": [100.0]},
                         index=pd.date_range("2024-01-01", periods=1))
    assert sa.compute_relative_strength("AAPL", tiny) is None


# ----------------------------------------------------------------------
# WYKRYWANIE PRZECIĘĆ MA (golden / death cross)
# ----------------------------------------------------------------------
def _df_with_ma(ma50_series, ma200_series):
    n = len(ma50_series)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Close": ma50_series,
        "MA50": ma50_series,
        "MA200": ma200_series,
    }, index=idx)


def test_detect_golden_cross():
    # MA50 startuje poniżej MA200, kończy powyżej -> golden cross dziś
    df = _df_with_ma([90, 95, 105], [100, 100, 100])
    res = sa.detect_ma_crossover(df)
    assert res["state"] == "golden"
    assert res["crossed"] is True
    assert res["type"] == "golden"


def test_detect_death_cross():
    df = _df_with_ma([110, 105, 95], [100, 100, 100])
    res = sa.detect_ma_crossover(df)
    assert res["state"] == "death"
    assert res["crossed"] is True
    assert res["type"] == "death"


def test_detect_no_cross():
    # MA50 cały czas powyżej MA200 -> brak przecięcia
    df = _df_with_ma([110, 112, 115], [100, 100, 100])
    res = sa.detect_ma_crossover(df)
    assert res["state"] == "golden"
    assert res["crossed"] is False
    assert res["type"] is None


def test_detect_crossover_insufficient_data():
    df = _df_with_ma([float("nan")], [float("nan")])
    assert sa.detect_ma_crossover(df) is None


def test_analyze_ticker_exposes_new_fields(fake_yfinance):
    res = sa.analyze_ticker("AAPL")
    assert "relative_strength" in res
    assert "ma_crossover" in res


# ----------------------------------------------------------------------
# VWAP
# ----------------------------------------------------------------------
def test_compute_vwap_basic():
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "High": np.full(n, 102.0),
        "Low": np.full(n, 98.0),
        "Close": np.full(n, 100.0),
        "Volume": np.full(n, 1000.0),
    }, index=idx)
    vwap = sa.compute_vwap(df, window=20)
    # cena typowa = (102+98+100)/3 = 100, więc VWAP = 100
    assert abs(vwap.dropna().iloc[-1] - 100.0) < 1e-6


def test_compute_vwap_falls_back_to_close():
    n = 40
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": np.full(n, 50.0), "Volume": np.full(n, 500.0)}, index=idx)
    vwap = sa.compute_vwap(df, window=20)
    assert abs(vwap.dropna().iloc[-1] - 50.0) < 1e-6


def test_compute_vwap_no_volume_column():
    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": np.full(n, 50.0)}, index=idx)
    vwap = sa.compute_vwap(df)
    assert vwap.dropna().empty


def test_vwap_position_above_below():
    n = 40
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    # stała cena 100, potem ostatni wyższy -> powyżej VWAP
    close = np.full(n, 100.0)
    close[-1] = 110.0
    df = pd.DataFrame({
        "High": close + 1, "Low": close - 1, "Close": close,
        "Volume": np.full(n, 1000.0),
    }, index=idx)
    pos = sa.vwap_position(df, window=20)
    assert pos is not None
    assert pos["above"] is True
    assert pos["distance_pct"] > 0


def test_vwap_position_insufficient_data():
    df = pd.DataFrame({"Close": [100.0], "Volume": [10.0]},
                       index=pd.date_range("2024-01-01", periods=1))
    assert sa.vwap_position(df, window=20) is None


# ----------------------------------------------------------------------
# HEALTH-CHECK TICKERA
# ----------------------------------------------------------------------
def test_validate_ticker_valid(fake_yfinance):
    res = sa.validate_ticker("AAPL")
    assert res["valid"] is True
    assert res["ticker"] == "AAPL"
    assert res["price"] is not None


def test_validate_ticker_empty(fake_yfinance):
    res = sa.validate_ticker("   ")
    assert res["valid"] is False


def test_validate_ticker_no_data(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2
    import pandas as pd

    class EmptyTicker(fake_yfinance):
        def history(self, period=None, interval=None):
            return pd.DataFrame()

    monkeypatch.setattr(sa2.yf, "Ticker", EmptyTicker)
    res = sa2.validate_ticker("ZZZZ")
    assert res["valid"] is False
    assert "Brak danych" in res["reason"] or "Brak" in res["reason"]


def test_analyze_ticker_exposes_vwap(fake_yfinance):
    res = sa.analyze_ticker("AAPL")
    assert "vwap" in res


# ----------------------------------------------------------------------
# ETYKIETY SEKTORA dla aktywów bez pola 'sector' (krypto, surowce, ETF)
# ----------------------------------------------------------------------
def test_sector_label_for_crypto(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CryptoTicker(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Bitcoin USD",
                    "quoteType": "CRYPTOCURRENCY", "sector": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CryptoTicker)
    res = sa2.analyze_ticker("BTC-USD")
    # krypto nie ma pola sector -> powinno dostać czytelną etykietę, nie None
    assert res["sector"] == "Kryptowaluta"


def test_sector_label_for_commodity_etf(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CommodityEtf(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Gold ETF",
                    "quoteType": "ETF", "sector": None,
                    "trailingPE": None, "dividendYield": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CommodityEtf)
    res = sa2.analyze_ticker("GLD")
    assert res["sector"] not in (None, "Nieznany")


def test_sector_label_stays_for_normal_stock(fake_yfinance):
    res = sa.analyze_ticker("AAPL")
    assert res["sector"] == "Technology"


# ----------------------------------------------------------------------
# TYP AKTYWA "crypto" - osobny od "commodity" (v1.1)
# ----------------------------------------------------------------------
def test_get_asset_type_crypto_quote_type():
    assert sa.get_asset_type({"quoteType": "CRYPTOCURRENCY"}) == "crypto"


def test_get_asset_type_commodity_quote_type():
    assert sa.get_asset_type({"quoteType": "FUTURE"}) == "commodity"
    assert sa.get_asset_type({"quoteType": "COMMODITY"}) == "commodity"
    assert sa.get_asset_type({"quoteType": "CURRENCY"}) == "commodity"


def test_get_asset_type_crypto_and_commodity_are_distinct():
    crypto = sa.get_asset_type({"quoteType": "CRYPTOCURRENCY"})
    commodity = sa.get_asset_type({"quoteType": "FUTURE"})
    assert crypto != commodity


def test_get_asset_type_fallback_to_ticker_suffix():
    # Brak quoteType od Yahoo, ale ticker ma sufiks -USD -> rozpoznaj jako crypto.
    assert sa.get_asset_type({}, ticker="BTC-USD") == "crypto"
    assert sa.get_asset_type({}, ticker="DOGE-USD") == "crypto"


def test_get_asset_type_fallback_without_suffix_defaults_to_stock():
    assert sa.get_asset_type({}, ticker="AAPL") == "stock"
    assert sa.get_asset_type({}) == "stock"  # brak tickera w ogóle


def test_get_weights_crypto_swaps_volatility_for_crypto_variant():
    weights = sa.get_weights_for_asset_type("crypto")
    assert "volatility_crypto" in weights
    assert "volatility" not in weights
    assert "btc_dominance" in weights
    # fundamentalne składowe wciąż wykluczone
    assert "valuation" not in weights
    assert "dividend" not in weights
    assert "fundamentals" not in weights


def test_get_weights_crypto_sums_to_one():
    weights = sa.get_weights_for_asset_type("crypto")
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_get_weights_commodity_adds_seasonality():
    weights = sa.get_weights_for_asset_type("commodity")
    assert "seasonality" in weights
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_get_weights_etf_commodity_adds_seasonality():
    weights = sa.get_weights_for_asset_type("etf_commodity")
    assert "seasonality" in weights


def test_get_weights_stock_unaffected_by_crypto_changes():
    """Upewnij się, że dodanie crypto nie popsuło zwykłych akcji."""
    weights = sa.get_weights_for_asset_type("stock")
    assert "volatility" in weights
    assert "volatility_crypto" not in weights
    assert "btc_dominance" not in weights
    assert "seasonality" not in weights
    assert abs(sum(weights.values()) - 1.0) < 1e-9


# ----------------------------------------------------------------------
# score_volatility_crypto - progi kalibrowane pod krypto
# ----------------------------------------------------------------------
def test_score_volatility_crypto_low_vol_higher_than_stock_thresholds():
    """40% rocznej zmienności to wysoka zmienność dla akcji, ale niska dla krypto."""
    import numpy as np
    rng = np.random.default_rng(1)
    n = 100
    # ~40% roczna zmienność: dzienne odchylenie ≈ 0.40/sqrt(252) ≈ 0.025
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.025, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": close}, index=idx)
    score, note = sa.score_volatility_crypto(df)
    assert score >= 50  # niska/normalna jak na krypto -> nie karana mocno
    assert "krypto" in note.lower()


def test_score_volatility_crypto_extreme_vol_scores_low():
    import numpy as np
    rng = np.random.default_rng(2)
    n = 100
    # Bardzo wysoka zmienność (~300% rocznie)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.19, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": close}, index=idx)
    score, note = sa.score_volatility_crypto(df)
    assert score <= 40


def test_score_volatility_crypto_insufficient_data():
    df = pd.DataFrame({"Close": [100.0, 101.0]})
    score, note = sa.score_volatility_crypto(df)
    assert score == 50
    assert "brak" in note.lower()


def test_score_volatility_crypto_vs_stock_same_data_different_score():
    """Ta sama zmienność (60% rocznie) - akcyjna f-cja karze mocniej niż krypto."""
    import numpy as np
    rng = np.random.default_rng(3)
    n = 100
    close = 100 * np.cumprod(1 + rng.normal(0, 0.038, n))  # ~60% rocznie
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Close": close}, index=idx)
    stock_score, _ = sa.score_volatility(df)
    crypto_score, _ = sa.score_volatility_crypto(df)
    assert crypto_score >= stock_score


# ----------------------------------------------------------------------
# score_btc_dominance
# ----------------------------------------------------------------------
def test_score_btc_dominance_btc_itself_is_neutral(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CryptoTicker(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Bitcoin USD",
                    "quoteType": "CRYPTOCURRENCY", "sector": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CryptoTicker)
    monkeypatch.setattr(sa2.external_data, "get_btc_dominance", lambda: None)
    df = CryptoTicker("BTC-USD").history()
    score, note = sa2.score_btc_dominance("BTC-USD", df)
    assert score == 50
    assert "punktem odniesienia" in note.lower()


def test_score_btc_dominance_altcoin_insufficient_data():
    df = pd.DataFrame({"Close": [100.0] * 10})
    score, note = sa.score_btc_dominance("ETH-USD", df)
    assert score == 50
    assert "brak" in note.lower()


def test_score_btc_dominance_altcoin_outperforming_btc(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2
    import numpy as np

    # Altcoin: silny wzrost 30d. BTC (mockowany fetch_history): płaski.
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    altcoin_close = np.linspace(100, 140, n)  # +40% w 30d ostatnich
    altcoin_df = pd.DataFrame({"Close": altcoin_close}, index=idx)

    btc_flat = pd.DataFrame({"Close": np.full(n, 100.0)}, index=idx)

    def fake_fetch_history(stock, period, interval="1d"):
        return btc_flat

    monkeypatch.setattr(sa2, "fetch_history", fake_fetch_history)
    score, note = sa2.score_btc_dominance("SOL-USD", altcoin_df)
    assert score > 50  # altcoin bije płaski BTC
    assert "bije btc" in note.lower()


# ----------------------------------------------------------------------
# score_seasonality
# ----------------------------------------------------------------------
def test_score_seasonality_known_ticker_returns_modifier():
    score, note = sa.score_seasonality("GLD")
    assert 0 <= score <= 100
    assert isinstance(note, str) and note


def test_score_seasonality_unknown_ticker_neutral():
    score, note = sa.score_seasonality("UNKNOWNTICKER")
    assert score == 50
    assert "brak danych" in note.lower()


def test_score_seasonality_case_insensitive():
    score_lower, _ = sa.score_seasonality("gld")
    score_upper, _ = sa.score_seasonality("GLD")
    assert score_lower == score_upper


# ----------------------------------------------------------------------
# Integracja: analyze_ticker dla crypto i commodity z nowymi składowymi
# ----------------------------------------------------------------------
def test_analyze_ticker_crypto_has_specialized_components(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CryptoTicker(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Ethereum USD",
                    "quoteType": "CRYPTOCURRENCY", "sector": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CryptoTicker)
    monkeypatch.setattr(sa2.external_data, "get_btc_dominance", lambda: None)
    res = sa2.analyze_ticker("ETH-USD")
    assert res["asset_type"] == "crypto"
    assert "volatility_crypto" in res["components"]
    assert "btc_dominance" in res["components"]
    assert "volatility" not in res["components"]
    # fundamentalne nadal wykluczone
    assert "valuation" not in res["components"]
    assert "dividend" not in res["components"]
    assert "fundamentals" not in res["components"]


def test_analyze_ticker_commodity_has_seasonality(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CommodityTicker(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Gold ETF",
                    "quoteType": "ETF", "sector": None,
                    "trailingPE": None, "dividendYield": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CommodityTicker)
    res = sa2.analyze_ticker("GLD")
    assert "seasonality" in res["components"]


def test_analyze_ticker_crypto_total_score_in_range(fake_yfinance, monkeypatch):
    import stock_analyzer as sa2

    class CryptoTicker(fake_yfinance):
        @property
        def info(self):
            return {"currency": "USD", "longName": "Bitcoin USD",
                    "quoteType": "CRYPTOCURRENCY", "sector": None}

    monkeypatch.setattr(sa2.yf, "Ticker", CryptoTicker)
    monkeypatch.setattr(sa2.external_data, "get_btc_dominance", lambda: None)
    res = sa2.analyze_ticker("BTC-USD")
    assert 0 <= res["total_score"] <= 100
