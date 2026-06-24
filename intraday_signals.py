# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Sygnały krótkoterminowe (swing/day-trading)
=============================================
Wskaźniki typowe dla krótkoterminowego tradingu: ATR (zasięg dziennych
ruchów), Stochastik (oscylator momentum wrażliwszy na krótkie odwrócenia
niż RSI), OBV (wolumen skumulowany, wykrywanie dywergencji) oraz proste
wykrywanie poziomów wsparcia/oporu.

WAŻNE OGRANICZENIE: wszystkie funkcje liczone są na danych DZIENNYCH
(interval='1d') z Yahoo Finance, opóźnionych ~15 minut. To NIE są dane
tick-by-tick ani nawet minutowe. Wskaźniki tutaj są więc bardziej
przydatne dla swing-tradingu (pozycje trzymane dni/tygodnie) niż dla
prawdziwego intraday day-tradingu (pozycje zamykane tego samego dnia).
Każda strona korzystająca z tego modułu powinna jasno komunikować to
ograniczenie użytkownikowi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# ATR - Average True Range
# ----------------------------------------------------------------------
def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Liczy ATR (Average True Range) - średni "prawdziwy zasięg" ruchu ceny.

    True Range to max z trzech wartości:
      1. High - Low (dzisiejszy zasięg)
      2. |High - poprzednie Close| (luka w górę)
      3. |Low - poprzednie Close| (luka w dół)

    ATR to krocząca średnia z True Range. Mówi "ile instrument zwykle
    porusza się w ciągu dnia" - kluczowe przy ustawianiu stop-lossów:
    stop ciaśniejszy niż ATR często zostanie "wybity" przez zwykły szum
    rynkowy, nie przez faktyczne odwrócenie trendu.

    Wymaga kolumn High, Low, Close. Zwraca serię pandas (te same jednostki
    co cena, np. USD).
    """
    if not {"High", "Low", "Close"}.issubset(df.columns):
        return pd.Series(index=df.index, dtype=float)

    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return true_range.rolling(window).mean()


def atr_summary(df: pd.DataFrame, window: int = 14) -> dict | None:
    """Zwraca podsumowanie ATR: wartość bezwzględna i jako % ceny.

    {atr, atr_pct, price} albo None, gdy brak danych.
    """
    atr_series = compute_atr(df, window=window)
    atr_series = atr_series.dropna()
    if atr_series.empty:
        return None

    last_atr = float(atr_series.iloc[-1])
    last_price = float(df["Close"].iloc[-1])
    if last_price == 0:
        return None

    return {
        "atr": round(last_atr, 4),
        "atr_pct": round(last_atr / last_price * 100, 2),
        "price": round(last_price, 4),
    }


# ----------------------------------------------------------------------
# STOCHASTIK - %K i %D
# ----------------------------------------------------------------------
def compute_stochastic(
    df: pd.DataFrame, k_window: int = 14, d_window: int = 3
) -> tuple[pd.Series, pd.Series]:
    """Liczy oscylator stochastyczny (%K i %D).

    %K = (Close - Low_n) / (High_n - Low_n) * 100, gdzie Low_n/High_n to
    minimum/maksimum z ostatnich k_window dni. Pokazuje, gdzie aktualna
    cena leży względem niedawnego zakresu wahań (0 = na minimum, 100 = na
    maksimum). %D to prosta średnia krocząca z %K (wygładzenie sygnału).

    W przeciwieństwie do RSI (który uśrednia zyski/straty), stochastik
    patrzy wyłącznie na POŁOŻENIE ceny w zakresie - bywa szybszy/bardziej
    czuły na krótkoterminowe odwrócenia, co czyni go popularnym narzędziem
    w handlu krótkoterminowym.

    Zwraca krotkę (%K, %D) jako serie pandas.
    """
    if not {"High", "Low", "Close"}.issubset(df.columns):
        empty = pd.Series(index=df.index, dtype=float)
        return empty, empty

    low_n = df["Low"].rolling(k_window).min()
    high_n = df["High"].rolling(k_window).max()
    denom = (high_n - low_n).replace(0, np.nan)

    percent_k = (df["Close"] - low_n) / denom * 100
    percent_d = percent_k.rolling(d_window).mean()

    return percent_k, percent_d


def stochastic_summary(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> dict | None:
    """Zwraca aktualny stan stochastyku z interpretacją.

    {k, d, signal, crossed} albo None.
    signal: 'wyprzedanie' (<20), 'przegrzanie' (>80), 'neutralnie'.
    crossed: 'bullish'/'bearish'/None - czy %K przecięło %D w ostatnim dniu.
    """
    k, d = compute_stochastic(df, k_window=k_window, d_window=d_window)
    k_valid, d_valid = k.dropna(), d.dropna()
    if k_valid.empty or d_valid.empty or len(k_valid) < 2 or len(d_valid) < 2:
        return None

    last_k, last_d = float(k_valid.iloc[-1]), float(d_valid.iloc[-1])
    prev_k, prev_d = float(k_valid.iloc[-2]), float(d_valid.iloc[-2])

    if last_k < 20:
        signal = "wyprzedanie"
    elif last_k > 80:
        signal = "przegrzanie"
    else:
        signal = "neutralnie"

    crossed = None
    if prev_k < prev_d and last_k > last_d:
        crossed = "bullish"
    elif prev_k > prev_d and last_k < last_d:
        crossed = "bearish"

    return {
        "k": round(last_k, 1),
        "d": round(last_d, 1),
        "signal": signal,
        "crossed": crossed,
    }


# ----------------------------------------------------------------------
# OBV - On-Balance Volume + dywergencja
# ----------------------------------------------------------------------
def compute_obv(df: pd.DataFrame) -> pd.Series:
    """Liczy OBV (On-Balance Volume) - skumulowany wolumen "ważony"
    kierunkiem ruchu ceny.

    Logika: jeśli cena dzisiaj wyższa niż wczoraj, dzisiejszy wolumen
    DODAJEMY do sumy; jeśli niższa - ODEJMUJEMY; bez zmiany - bez zmian.
    OBV pokazuje, czy wolumen "popiera" ruch ceny. Sama wartość OBV nie
    ma jednostki w sensie fizycznym - liczy się jej KIERUNEK i czy zgadza
    się z kierunkiem ceny (patrz detect_obv_divergence niżej).
    """
    if "Volume" not in df.columns:
        return pd.Series(index=df.index, dtype=float)

    close = df["Close"]
    volume = df["Volume"]
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def detect_obv_divergence(df: pd.DataFrame, window: int = 20) -> dict | None:
    """Wykrywa dywergencję ceny i OBV w ostatnim oknie `window` dni.

    Dywergencja = cena i wolumen "mówią co innego". Dwa typy:
      - Bearish (niedźwiedzia): cena robi nowe maksimum, ale OBV NIE robi
        nowego maksimum -> wzrost ceny nie jest "popierany" wolumenem,
        sugeruje słabnący popyt mimo rosnącej ceny.
      - Bullish (bycza): cena robi nowe minimum, ale OBV NIE robi nowego
        minimum -> spadek ceny nie jest "popierany" sprzedażą, sugeruje
        słabnącą podaż mimo spadającej ceny.

    Zwraca {type, description} albo None (brak danych lub brak dywergencji
    w badanym oknie).
    """
    obv = compute_obv(df)
    if obv.empty or len(obv.dropna()) < window:
        return None

    price_window = df["Close"].iloc[-window:]
    obv_window = obv.iloc[-window:]

    price_now, price_max, price_min = price_window.iloc[-1], price_window.max(), price_window.min()
    obv_now, obv_max, obv_min = obv_window.iloc[-1], obv_window.max(), obv_window.min()

    # Cena na nowym maksimum okna, ale OBV nie potwierdza (nie jest na swoim maksimum).
    price_at_high = price_now >= price_max * 0.999  # tolerancja zaokrągleń
    obv_at_high = obv_now >= obv_max * 0.999 if obv_max != 0 else True

    if price_at_high and not obv_at_high:
        return {
            "type": "bearish",
            "description": (
                "Cena na nowym maksimum okna, ale wolumen (OBV) tego nie "
                "potwierdza – możliwy sygnał słabnącego popytu mimo wzrostu ceny."
            ),
        }

    price_at_low = price_now <= price_min * 1.001
    obv_at_low = obv_now <= obv_min * 1.001 if obv_min != 0 else True

    if price_at_low and not obv_at_low:
        return {
            "type": "bullish",
            "description": (
                "Cena na nowym minimum okna, ale wolumen (OBV) tego nie "
                "potwierdza – możliwy sygnał słabnącej podaży mimo spadku ceny."
            ),
        }

    return None


# ----------------------------------------------------------------------
# POZIOMY WSPARCIA I OPORU
# ----------------------------------------------------------------------
def detect_support_resistance(
    df: pd.DataFrame, window: int = 10, lookback: int = 120, max_levels: int = 4
) -> dict:
    """Wykrywa poziomy wsparcia i oporu na bazie lokalnych ekstremów ceny.

    Metoda: szuka dni, gdzie Low było najniższe w otoczeniu +/- `window`
    dni (lokalne minimum -> kandydat na wsparcie) i analogicznie dla High
    (lokalne maksimum -> kandydat na opór). Patrzy tylko na ostatnie
    `lookback` dni (starsze poziomy są mniej istotne dla bieżącej sytuacji).
    Blisko leżące poziomy (w obrębie 1.5% ceny) są grupowane w jeden,
    żeby nie zaśmiecać wykresu prawie identycznymi liniami.

    Zwraca {support: [poziomy rosnąco], resistance: [poziomy rosnąco]} -
    obie listy ograniczone do max_levels najistotniejszych (najbliższych
    aktualnej cenie, bo te są praktycznie najważniejsze).
    """
    if not {"High", "Low"}.issubset(df.columns) or df.empty:
        return {"support": [], "resistance": []}

    recent = df.iloc[-lookback:] if len(df) > lookback else df
    if len(recent) < window * 2 + 1:
        return {"support": [], "resistance": []}

    current_price = float(df["Close"].iloc[-1])

    lows = recent["Low"]
    highs = recent["High"]

    support_candidates = []
    resistance_candidates = []

    for i in range(window, len(recent) - window):
        local_low = lows.iloc[i - window:i + window + 1]
        if lows.iloc[i] == local_low.min():
            support_candidates.append(float(lows.iloc[i]))

        local_high = highs.iloc[i - window:i + window + 1]
        if highs.iloc[i] == local_high.max():
            resistance_candidates.append(float(highs.iloc[i]))

    def _cluster(levels: list[float], tolerance_pct: float = 1.5) -> list[float]:
        """Grupuje blisko leżące poziomy (w obrębie tolerance_pct%) w jeden."""
        if not levels:
            return []
        levels = sorted(set(levels))
        clustered = [levels[0]]
        for lvl in levels[1:]:
            if abs(lvl - clustered[-1]) / clustered[-1] * 100 > tolerance_pct:
                clustered.append(lvl)
            else:
                clustered[-1] = (clustered[-1] + lvl) / 2  # uśrednij blisko leżące
        return clustered

    support_levels = _cluster(support_candidates)
    resistance_levels = _cluster(resistance_candidates)

    # Najistotniejsze = najbliższe aktualnej cenie.
    support_levels = sorted(support_levels, key=lambda x: abs(x - current_price))[:max_levels]
    resistance_levels = sorted(resistance_levels, key=lambda x: abs(x - current_price))[:max_levels]

    return {
        "support": sorted(round(s, 4) for s in support_levels),
        "resistance": sorted(round(r, 4) for r in resistance_levels),
    }
