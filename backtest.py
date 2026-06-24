# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Backtesting prostej strategii score
======================================
Sprawdza, "co by było, gdyby" kupować spółkę, gdy uproszczony techniczny
score przekroczy próg "kupna", i sprzedawać, gdy spadnie poniżej progu
"sprzedaży" - porównane z prostym "kup i trzymaj" (buy & hold).

Dodatkowe narzędzia:
- run_threshold_grid()  - testuje wiele kombinacji progów kupna/sprzedaży
                           naraz (do heatmapy) - pomaga zobaczyć, czy 65/35
                           było "dobrym wyborem", czy przypadkiem
- walk_forward_analysis() - dzieli historię na kilka okresów i testuje
                           regułę w każdym z nich osobno - pomaga ocenić,
                           czy reguła jest stabilna w czasie, czy działała
                           tylko w jednym, konkretnym okresie

WAŻNE OGRANICZENIA (czytaj przed wnioskami!):
- Score używany tutaj to UPROSZCZONA wersja (RSI + trend + MACD) - taka,
  którą można policzyć dla każdego dnia historii. Pełny score z dashboardu
  zawiera też wycenę, dywidendę, fundamenty i sentyment, które nie mają
  pełnej historii dziennej z yfinance.
- Brak kosztów transakcyjnych, podatków, spreadu, poślizgu cenowego.
- Wynik na danych historycznych NIE gwarantuje wyników w przyszłości
  (overfitting, zmiana warunków rynkowych itp.)
- To narzędzie EDUKACYJNE do zrozumienia, jak działałaby reguła "score > X",
  nie gotowa strategia do realnego handlu.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from stock_analyzer import rsi, macd, compute_simple_score_series

TRADING_DAYS_PER_YEAR = 252


# ----------------------------------------------------------------------
# DANE
# ----------------------------------------------------------------------
def _load_score_series(ticker: str, period: str):
    """Pobiera dane i liczy uproszczony score dla każdego dnia. None jeśli brak danych."""
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval="1d")
    if df.empty or len(df) < 210:
        return None

    df["RSI"] = rsi(df["Close"])
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = macd(df["Close"])

    score_df = compute_simple_score_series(df)
    if len(score_df) < 30:
        return None

    return score_df.set_index("Date")


# ----------------------------------------------------------------------
# METRYKI RYZYKA
# ----------------------------------------------------------------------
def _risk_metrics(equity: pd.Series) -> dict:
    """
    Liczy Sharpe ratio i Sortino ratio na podstawie dziennych zwrotów
    krzywej equity. Zakłada stopę bezpieczną = 0 (uproszczenie - w
    realnych obliczeniach odejmuje się stopę wolną od ryzyka).

    Sharpe  = średni dzienny zwrot / odchylenie std dziennych zwrotów,
              zannualizowane (* sqrt(252))
    Sortino = jak Sharpe, ale w mianowniku tylko odchylenie std
              UJEMNYCH zwrotów (kara tylko za "złą" zmienność)
    """
    returns = equity.pct_change().dropna()
    if len(returns) < 2 or returns.std() == 0:
        return {"sharpe": 0.0, "sortino": 0.0}

    mean_ret = returns.mean()
    std_ret = returns.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(TRADING_DAYS_PER_YEAR)

    downside = returns[returns < 0]
    if len(downside) == 0 or downside.std() == 0:
        sortino = sharpe  # brak ujemnych zwrotów - traktuj jak Sharpe
    else:
        sortino = (mean_ret / downside.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

    return {"sharpe": round(float(sharpe), 2), "sortino": round(float(sortino), 2)}


# ----------------------------------------------------------------------
# SYMULACJA
# ----------------------------------------------------------------------
def _simulate(
    prices: pd.Series,
    scores: pd.Series,
    buy_threshold: float,
    sell_threshold: float,
    initial_capital: float,
) -> dict:
    """Symuluje strategię 'score' na podanym wycinku cen/score. Zwraca equity_curve, trades, metrics."""
    in_position = False
    entry_price = None
    entry_date = None
    trades = []

    strategy_value = []
    capital = initial_capital
    shares = 0.0

    for date, price in prices.items():
        score = scores.loc[date]

        if not in_position and score >= buy_threshold:
            shares = capital / price
            capital = 0.0
            in_position = True
            entry_price = price
            entry_date = date

        elif in_position and score <= sell_threshold:
            capital = shares * price
            ret_pct = (price / entry_price - 1) * 100
            trades.append({
                "kupno": entry_date,
                "sprzedaz": date,
                "cena_kupna": round(entry_price, 2),
                "cena_sprzedazy": round(price, 2),
                "zwrot_%": round(ret_pct, 2),
            })
            shares = 0.0
            in_position = False
            entry_price = None
            entry_date = None

        total_value = capital + shares * price
        strategy_value.append(total_value)

    if in_position:
        final_price = prices.iloc[-1]
        ret_pct = (final_price / entry_price - 1) * 100
        trades.append({
            "kupno": entry_date,
            "sprzedaz": prices.index[-1],
            "cena_kupna": round(entry_price, 2),
            "cena_sprzedazy": round(final_price, 2),
            "zwrot_%": round(ret_pct, 2),
            "uwaga": "pozycja wciąż otwarta na koniec okresu",
        })

    buyhold_shares = initial_capital / prices.iloc[0]
    buyhold_value = buyhold_shares * prices

    equity_curve = pd.DataFrame({
        "Date": prices.index,
        "Strategy": strategy_value,
        "BuyHold": buyhold_value.values,
    })

    total_return = (strategy_value[-1] / initial_capital - 1) * 100
    buyhold_return = (buyhold_value.iloc[-1] / initial_capital - 1) * 100

    wins = [t for t in trades if t["zwrot_%"] > 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0

    equity_series = equity_curve["Strategy"]
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    risk = _risk_metrics(equity_series)

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": {
            "total_return": round(total_return, 1),
            "buyhold_return": round(buyhold_return, 1),
            "num_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "max_drawdown": round(float(max_drawdown), 1),
            "final_value": round(strategy_value[-1], 2),
            "buyhold_final_value": round(buyhold_value.iloc[-1], 2),
            "still_open": in_position,
            "sharpe": risk["sharpe"],
            "sortino": risk["sortino"],
        },
    }


# ----------------------------------------------------------------------
# GŁÓWNA FUNKCJA BACKTESTU
# ----------------------------------------------------------------------
def backtest_score_strategy(
    ticker: str,
    period: str = "2y",
    buy_threshold: float = 65,
    sell_threshold: float = 35,
    initial_capital: float = 10_000,
) -> dict:
    """
    Strategia: kup gdy score >= buy_threshold (i nie mamy pozycji),
    sprzedaj gdy score <= sell_threshold (i mamy pozycję).

    Zwraca dict z:
    - equity_curve: DataFrame (Date, Strategy, BuyHold)
    - trades: lista transakcji (data kupna, data sprzedaży, zwrot %)
    - metrics: total_return, buyhold_return, num_trades, win_rate,
               max_drawdown, sharpe, sortino
    """
    score_df = _load_score_series(ticker, period)
    if score_df is None:
        return {"error": "Niewystarczająca ilość danych historycznych (potrzeba min. ~210 dni)."}

    return _simulate(score_df["Close"], score_df["Score"], buy_threshold, sell_threshold, initial_capital)


# ----------------------------------------------------------------------
# HEATMAPA PROGÓW
# ----------------------------------------------------------------------
def run_threshold_grid(
    ticker: str,
    period: str = "2y",
    buy_range=range(50, 91, 5),
    sell_range=range(10, 51, 5),
    initial_capital: float = 10_000,
) -> dict:
    """
    Testuje wiele kombinacji (buy_threshold, sell_threshold) na tych samych
    danych i zwraca tabelę wyników - do narysowania heatmapy.

    Zwraca:
    - grid: DataFrame, indeks = sell_threshold, kolumny = buy_threshold,
            wartości = total_return (%)
    - best: najlepsza kombinacja (buy, sell, return)
    - buyhold_return: zwrot 'kup i trzymaj' w tym okresie (punkt odniesienia)
    """
    score_df = _load_score_series(ticker, period)
    if score_df is None:
        return {"error": "Niewystarczająca ilość danych historycznych (potrzeba min. ~210 dni)."}

    prices, scores = score_df["Close"], score_df["Score"]

    results = []
    best = None
    buyhold_return = None

    for buy in buy_range:
        for sell in sell_range:
            if buy <= sell:
                continue
            sim = _simulate(prices, scores, buy, sell, initial_capital)
            ret = sim["metrics"]["total_return"]
            if buyhold_return is None:
                buyhold_return = sim["metrics"]["buyhold_return"]
            results.append({"buy": buy, "sell": sell, "return": ret})
            if best is None or ret > best["return"]:
                best = {"buy": buy, "sell": sell, "return": ret}

    if not results:
        return {"error": "Brak poprawnych kombinacji progów (buy musi być > sell)."}

    df_results = pd.DataFrame(results)
    grid = df_results.pivot(index="sell", columns="buy", values="return")

    return {"grid": grid, "best": best, "buyhold_return": buyhold_return}


# ----------------------------------------------------------------------
# WALK-FORWARD (test stabilności reguły w czasie)
# ----------------------------------------------------------------------
def walk_forward_analysis(
    ticker: str,
    period: str = "5y",
    buy_threshold: float = 65,
    sell_threshold: float = 35,
    n_windows: int = 4,
    initial_capital: float = 10_000,
) -> dict:
    """
    Dzieli historię na `n_windows` równych, NIEPRZYKRYWAJĄCYCH SIĘ okresów
    i uruchamia tę samą regułę w każdym z nich od nowa (z tym samym
    kapitałem startowym). Pomaga ocenić, czy reguła działa konsekwentnie,
    czy tylko w jednym, szczególnym okresie (np. silny rynek wzrostowy).

    Zwraca listę wyników per okno + podsumowanie (ile okien strategia
    pokonała 'kup i trzymaj').
    """
    score_df = _load_score_series(ticker, period)
    if score_df is None:
        return {"error": "Niewystarczająca ilość danych historycznych (potrzeba min. ~210 dni)."}

    n = len(score_df)
    if n < n_windows * 60:
        return {"error": f"Za mało danych na {n_windows} okien - spróbuj dłuższy okres lub mniej okien."}

    window_size = n // n_windows
    windows = []

    for i in range(n_windows):
        start = i * window_size
        end = n if i == n_windows - 1 else (i + 1) * window_size
        chunk = score_df.iloc[start:end]
        if len(chunk) < 30:
            continue

        sim = _simulate(chunk["Close"], chunk["Score"], buy_threshold, sell_threshold, initial_capital)
        m = sim["metrics"]
        windows.append({
            "okres_od": chunk.index[0].date().isoformat(),
            "okres_do": chunk.index[-1].date().isoformat(),
            "strategia_%": m["total_return"],
            "kup_i_trzymaj_%": m["buyhold_return"],
            "lepsza_niz_bh": m["total_return"] > m["buyhold_return"],
            "liczba_transakcji": m["num_trades"],
            "max_obsuniecie_%": m["max_drawdown"],
        })

    if not windows:
        return {"error": "Nie udało się policzyć żadnego okna."}

    wins = sum(1 for w in windows if w["lepsza_niz_bh"])

    return {
        "windows": windows,
        "summary": {
            "n_windows": len(windows),
            "wins": wins,
            "win_rate_pct": round(wins / len(windows) * 100, 0),
        },
    }
