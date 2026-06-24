# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Moduł Strategii Inwestycyjnych
================================
Sprawdza, czy dana spółka aktualnie spełnia kryteria popularnych
strategii/podejść inwestycyjnych. Zwraca checklistę warunków
(spełniony / niespełniony) + ogólną ocenę "zgodności" ze strategią.

To NIE są gotowe sygnały "kup/sprzedaj" - to checklisty pomagające
ocenić, czy spółka pasuje do danego stylu inwestowania.
"""

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# DEFINICJE STRATEGII
# Każda strategia to lista warunków (funkcja, opis, etykieta)
# Funkcja przyjmuje (df, info, components) i zwraca (bool, opis_wartości)
# ----------------------------------------------------------------------

def _trend_following_conditions(df, info, components):
    price = df["Close"].iloc[-1]
    ma50 = df["MA50"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]
    macd_val = df["MACD"].iloc[-1]
    macd_sig = df["MACD_signal"].iloc[-1]
    rsi_val = df["RSI"].iloc[-1]

    return [
        (
            "Cena powyżej średniej 200-dniowej",
            price > ma200,
            f"cena={price:.2f}, MA200={ma200:.2f}",
        ),
        (
            "Cena powyżej średniej 50-dniowej",
            price > ma50,
            f"cena={price:.2f}, MA50={ma50:.2f}",
        ),
        (
            "Średnia 50-dniowa powyżej 200-dniowej (złoty krzyż)",
            ma50 > ma200,
            f"MA50={ma50:.2f}, MA200={ma200:.2f}",
        ),
        (
            "MACD wskazuje trend wzrostowy",
            macd_val > macd_sig,
            f"MACD={macd_val:.2f}, sygnał={macd_sig:.2f}",
        ),
        (
            "RSI nie jest jeszcze 'przegrzane' (poniżej 70)",
            rsi_val < 70,
            f"RSI={rsi_val:.1f}",
        ),
    ]


def _mean_reversion_conditions(df, info, components):
    rsi_val = df["RSI"].iloc[-1]
    price = df["Close"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]
    close = df["Close"]
    chg_1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100 if len(close) >= 22 else np.nan

    return [
        (
            "RSI wskazuje na wyprzedanie (poniżej 35)",
            rsi_val < 35,
            f"RSI={rsi_val:.1f}",
        ),
        (
            "Cena spadła w ostatnim miesiącu",
            chg_1m < 0,
            f"zmiana 1M={chg_1m:.1f}%" if not np.isnan(chg_1m) else "brak danych",
        ),
        (
            "Spadek nie jest ekstremalny (mniej niż -25% w miesiącu)",
            chg_1m > -25 if not np.isnan(chg_1m) else False,
            f"zmiana 1M={chg_1m:.1f}%" if not np.isnan(chg_1m) else "brak danych",
        ),
        (
            "Cena wciąż blisko długoterminowego trendu (nie więcej niż 30% pod MA200)",
            price > ma200 * 0.7,
            f"cena={price:.2f}, MA200={ma200:.2f}",
        ),
    ]


def _value_long_term_conditions(df, info, components):
    pe = info.get("trailingPE")
    peg = info.get("pegRatio")
    payout = info.get("payoutRatio")
    div_yield = info.get("dividendYield")
    profit_margin = info.get("profitMargins")

    pe_ok = pe is not None and 0 < pe < 25
    peg_ok = peg is not None and peg < 1.5
    profit_ok = profit_margin is not None and profit_margin > 0
    div_ok = div_yield is not None and div_yield > 0
    payout_ok = payout is not None and payout < 0.8

    return [
        (
            "Wskaźnik P/E jest umiarkowany (poniżej 25)",
            pe_ok,
            f"P/E={pe:.1f}" if pe else "brak danych",
        ),
        (
            "Firma jest rentowna (dodatnia marża zysku)",
            profit_ok,
            f"marża={profit_margin:.1%}" if profit_margin is not None else "brak danych",
        ),
        (
            "PEG wskazuje na rozsądną cenę względem wzrostu (poniżej 1.5)",
            peg_ok,
            f"PEG={peg:.2f}" if peg else "brak danych",
        ),
        (
            "Spółka wypłaca dywidendę",
            div_ok,
            f"yield={div_yield:.2%}" if div_yield else "brak dywidendy",
        ),
        (
            "Dywidenda wygląda bezpiecznie (payout < 80%)",
            payout_ok,
            f"payout={payout:.0%}" if payout is not None else "brak danych",
        ),
    ]


def _momentum_breakout_conditions(df, info, components):
    close = df["Close"]
    high_52w = close.rolling(252).max().iloc[-1] if len(close) >= 252 else close.max()
    price = close.iloc[-1]
    vol = df["Volume"]
    avg_vol = vol.rolling(20).mean().iloc[-1]
    last_vol = vol.iloc[-1]
    chg_1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100 if len(close) >= 22 else np.nan
    rsi_val = df["RSI"].iloc[-1]

    near_high = price >= high_52w * 0.95

    return [
        (
            "Cena jest blisko (max 5% poniżej) szczytu z ostatnich 52 tygodni",
            near_high,
            f"cena={price:.2f}, 52w max={high_52w:.2f}",
        ),
        (
            "Silny wzrost w ostatnim miesiącu (powyżej +5%)",
            chg_1m > 5 if not np.isnan(chg_1m) else False,
            f"zmiana 1M={chg_1m:.1f}%" if not np.isnan(chg_1m) else "brak danych",
        ),
        (
            "Zwiększony wolumen (powyżej średniej z 20 dni)",
            last_vol > avg_vol,
            f"wolumen={last_vol:,.0f}, śr.20d={avg_vol:,.0f}",
        ),
        (
            "RSI wskazuje silny, ale nie ekstremalny moment (50-85)",
            50 <= rsi_val <= 85,
            f"RSI={rsi_val:.1f}",
        ),
    ]


STRATEGIE = {
    "trend_following": {
        "nazwa": "Trend Following (jazda z trendem)",
        "opis": (
            "Podejście dla osób, które chcą inwestować 'z prądem' - "
            "kupować spółki, które już są w trendzie wzrostowym, "
            "i trzymać je tak długo, jak trend trwa. "
            "Typowy horyzont: tygodnie-miesiące."
        ),
        "conditions_fn": _trend_following_conditions,
        "ikona": "📈",
    },
    "mean_reversion": {
        "nazwa": "Dip Buying / Mean Reversion (kupowanie spadków)",
        "opis": (
            "Podejście dla osób szukających spółek, które niedawno "
            "spadły i mogą być 'wyprzedane' - z założeniem, że cena "
            "wróci bliżej swojej średniej. Wyższe ryzyko - spadek "
            "może mieć dobry powód."
        ),
        "conditions_fn": _mean_reversion_conditions,
        "ikona": "📉",
    },
    "value_long_term": {
        "nazwa": "Value / Długoterminowe (jakość + rozsądna cena)",
        "opis": (
            "Podejście dla inwestorów długoterminowych - szukanie "
            "rentownych, stabilnych firm, które nie są przewartościowane "
            "i (opcjonalnie) wypłacają dywidendę. Typowy horyzont: lata."
        ),
        "conditions_fn": _value_long_term_conditions,
        "ikona": "🏛️",
    },
    "momentum_breakout": {
        "nazwa": "Momentum / Breakout (przełamanie szczytów)",
        "opis": (
            "Podejście dla osób szukających spółek 'w ogniu' - blisko "
            "nowych szczytów cenowych, z dużym zainteresowaniem rynku. "
            "Wysokie ryzyko i zmienność - wymaga aktywnego śledzenia."
        ),
        "conditions_fn": _momentum_breakout_conditions,
        "ikona": "🚀",
    },
}


def evaluate_strategy(strategy_key: str, df: pd.DataFrame, info: dict, components: dict) -> dict:
    """
    Sprawdza, ile warunków danej strategii jest spełnionych.
    Zwraca dict z listą warunków i ogólnym wynikiem zgodności (0-100).
    """
    strategy = STRATEGIE[strategy_key]
    conditions = strategy["conditions_fn"](df, info, components)

    met = sum(1 for _, ok, _ in conditions if ok)
    total = len(conditions)
    match_pct = (met / total * 100) if total else 0

    return {
        "nazwa": strategy["nazwa"],
        "opis": strategy["opis"],
        "ikona": strategy["ikona"],
        "conditions": conditions,
        "met": met,
        "total": total,
        "match_pct": round(match_pct, 0),
    }


def interpret_match(match_pct: float) -> str:
    if match_pct >= 80:
        return "Spółka silnie spełnia kryteria tej strategii"
    if match_pct >= 50:
        return "Spółka częściowo spełnia kryteria tej strategii"
    return "Spółka nie spełnia większości kryteriów tej strategii"
