# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
common.py – współdzielone stałe, funkcje pomocnicze i funkcje cache'ujące
=========================================================================
Importowane przez app.py i każdą stronę w pages/.
NIE zawiera żadnych wywołań st.* na poziomie modułu – tylko definicje.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import external_data

from stock_analyzer import (
    WEIGHTS,
    INDICATOR_NAMES,
    analyze_ticker,
    interpret_score,
    rsi,
    macd,
    bollinger_bands,
    compute_vwap,
    search_tickers,
    compute_simple_score_series,
)

# ── Kolory ────────────────────────────────────────────────────────────
# ── Paleta kolorów StockFlow Brand Guide ──────────────────────────────
# Źródło: brand guide StockFlow (zielony #22C55E, teal #14B8A6, niebieski #3B82F6)
KOLOR_DOBRY     = "#22C55E"   # brand primary green  — sygnały pozytywne
KOLOR_NEUTRALNY = "#64748B"   # slate-500            — stan neutralny
KOLOR_SLABY     = "#EF4444"   # red-500              — sygnały negatywne
KOLOR_AKCENTU   = "#14B8A6"   # brand teal           — akcenty, wykresy, linki
KOLOR_BLUE      = "#3B82F6"   # brand blue           — wykresy, MA, info
KOLOR_TLO       = "#1F2937"   # brand dark bg
KOLOR_TLO2      = "#111827"   # brand darker bg (sidebar)
KOLOR_TEKST     = "#F8FAFC"   # brand light text

LEGENDA_SCORE = (
    "🟢 60-100: więcej sygnałów 'pozytywnych'\n\n"
    "⚪ 40-60: brak wyraźnego sygnału\n\n"
    "🔴 0-40: więcej sygnałów 'negatywnych'\n\n"
    "Wynik NIE przewiduje przyszłości – opisuje tylko obecną sytuację."
)

# ── Opisy wskaźników (używane w tab 'Szczegóły wyniku' i 'Co to znaczy?') ─
OPISY_WSKAZNIKOW: dict[str, dict] = {
    "rsi":          {"nazwa": "Siła trendu (RSI)",
                     "opis": "Sprawdza, czy spółka jest 'wyprzedana' (mogła spaść za dużo) albo 'przegrzana' (wzrosła za szybko)."},
    "trend_ma":     {"nazwa": "Kierunek trendu",
                     "opis": "Porównuje cenę ze średnią z ostatnich 50 i 200 dni. Pokazuje, czy spółka jest w trendzie wzrostowym czy spadkowym."},
    "macd":         {"nazwa": "Zmiana momentum (MACD)",
                     "opis": "Wykrywa, kiedy tempo wzrostu lub spadku ceny zaczyna się zmieniać – wczesny sygnał zwrotu trendu."},
    "volume":       {"nazwa": "Zainteresowanie inwestorów (wolumen)",
                     "opis": "Sprawdza, czy ostatnio handlowano spółką częściej niż zwykle – duże zainteresowanie może oznaczać ważny ruch."},
    "volatility":   {"nazwa": "Stabilność ceny",
                     "opis": "Mierzy, jak bardzo cena 'skacze' w górę i w dół. Mniejsze skoki = mniej nerwowa inwestycja."},
    "valuation":    {"nazwa": "Wycena (P/E)",
                     "opis": "Porównuje cenę akcji z zyskami firmy. Pomaga ocenić, czy spółka jest tania czy droga względem tego, co zarabia."},
    "momentum":     {"nazwa": "Ostatnie zmiany ceny",
                     "opis": "Pokazuje, jak bardzo zmieniła się cena w ostatnim miesiącu i kwartale."},
    "dividend":     {"nazwa": "Dywidenda",
                     "opis": "Sprawdza, czy spółka wypłaca dywidendę, jak wysoka jest jej stopa i czy wypłaty są bezpieczne."},
    "sentiment":    {"nazwa": "Sentyment newsów",
                     "opis": "Sprawdza ton ostatnich nagłówków newsów – więcej pozytywnych słów podnosi wynik, negatywnych obniża."},
    "fundamentals": {"nazwa": "Fundamenty (wzrost, ROE, dług, CF)",
                     "opis": "Patrzy na wzrost przychodów/zysku, zadłużenie i wolny cash flow – 'pod maską' firmy."},
    # Składowe specyficzne dla krypto (od v1.1)
    "volatility_crypto": {"nazwa": "Stabilność ceny (kalibracja krypto)",
                          "opis": "Mierzy zmienność ceny w skali typowej dla rynku krypto – 50–120% rocznie to norma, nie anomalia. Progi inne niż dla akcji."},
    "btc_dominance":     {"nazwa": "Siła względem Bitcoina",
                          "opis": "Porównuje 30-dniowy zwrot tej kryptowaluty z Bitcoinem. Altcoin bijący BTC sugeruje większe zainteresowanie rynku tym projektem."},
    # Składowe specyficzne dla surowców (od v1.1)
    "seasonality":       {"nazwa": "Sezonowość surowca",
                          "opis": "Modyfikator oparty na historycznych wzorcach sezonowych popytu/podaży (np. złoto silniejsze Q4/Q1, gaz ziemny silniejszy zimą). Orientacyjna tendencja, nie gwarancja."},
    # Składowe score krótkoterminowego (od v1.1)
    "rsi_st":      {"nazwa": "RSI-7 (krótkie okno)",
                    "opis": "RSI z oknem 7 dni – bardziej czuły na krótkoterminowe odwrócenia niż standardowy RSI-14. Poniżej 25 = silne wyprzedanie, powyżej 75 = silne przegrzanie."},
    "stoch_st":    {"nazwa": "Stochastik %K",
                    "opis": "Gdzie leży aktualna cena w zakresie ostatnich 14 dni. Poniżej 20 = wyprzedanie, powyżej 80 = przegrzanie. Czulszy na krótkie odwrócenia niż RSI."},
    "momentum_st": {"nazwa": "Momentum 5d/10d",
                    "opis": "Zmiana ceny w ostatnich 5 i 10 dniach. Oba dodatnie = trend wzrostowy potwierdzony; oba ujemne = spójny trend spadkowy."},
    "volume_st":   {"nazwa": "Wolumen 3d vs 10d",
                    "opis": "Średni wolumen z ostatnich 3 dni względem średniej z 10 dni. Wysoki wolumen + wzrost ceny = siła popytu; wysoki + spadek = siła podaży."},
    "obv_st":      {"nazwa": "OBV – kierunek wolumenu",
                    "opis": "Czy On-Balance Volume rośnie czy spada w ostatnich 5 dniach, i czy zgadza się z kierunkiem ceny. Dywergencja może sygnalizować zbliżające się odwrócenie."},
    "vwap_st":     {"nazwa": "Pozycja względem VWAP",
                    "opis": "Gdzie leży cena względem VWAP (średniej ważonej wolumenem z 20 dni). Powyżej VWAP = kupujący płacą więcej niż średnia handlowa (siła popytu)."},
    "bb_st":       {"nazwa": "Bollinger %B",
                    "opis": "Gdzie leży cena w wstędze Bollingera (0 = dolna, 1 = górna). Poniżej 0.05 = silne wyprzedanie przy dolnej wstędze; powyżej 0.95 = przegrzanie przy górnej."},
}

DISCLAIMER = (
    "⚠️ **Disclaimer**: To narzędzie ma charakter edukacyjny/analityczny "
    "i nie stanowi porady inwestycyjnej. Dane pochodzą z Yahoo Finance "
    "i mogą być nieaktualne lub niedokładne. "
    "Decyzje inwestycyjne podejmujesz na własną odpowiedzialność."
)

# Wersja aplikacji - pokazywana w stopce. Ułatwia powiązanie zgłoszeń
# testerów z konkretnym stanem kodu. Podnoś przy każdym wydaniu.
APP_VERSION = "1.1.0"

# ⬇️ PODMIEŃ na swój formularz Google / GitHub Issues przed publicznym launchem.
# Używane w stopce (footer) i na stronie „O aplikacji”.
FEEDBACK_URL = "https://forms.gle/your-feedback-form"


# ── Motyw wykresów ────────────────────────────────────────────────────
def get_plotly_template() -> str:
    return "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"


def apply_theme(fig: go.Figure) -> go.Figure:
    """Stosuje brand guide StockFlow do wykresu Plotly.

    Przezroczyste tło (dopasowuje się do tła Streamlit), brand grid i font.
    """
    fig.update_layout(
        template=get_plotly_template(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=KOLOR_TEKST),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            linecolor="rgba(255,255,255,0.10)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            linecolor="rgba(255,255,255,0.10)",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12),
        ),
    )
    return fig


# ── Pomocniki score ───────────────────────────────────────────────────
def kolor_dla_score(score: float) -> str:
    if score >= 60:
        return KOLOR_DOBRY
    if score >= 40:
        return KOLOR_NEUTRALNY
    return KOLOR_SLABY


def emoji_dla_score(score: float) -> str:
    if score >= 60:
        return "🟢"
    if score >= 40:
        return "⚪"
    return "🔴"


def badge_score(score: float) -> str:
    """Zwraca czytelny badge, np. '🟢 72 / 100'."""
    return f"{emoji_dla_score(score)} {score:.0f} / 100"


# ── Dane (cache) ──────────────────────────────────────────────────────
def _pobierz_dane_core(ticker: str, period: str = "1y"):
    """Czysta logika pobrania + wyliczenia wskaźników (bez cache).

    Współdzielona przez pobierz_dane (TTL 15 min) i pobierz_dane_live (TTL 60 s).
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval="1d")
    if df.empty:
        return None, None
    # Usuń wiersze z brakującą ceną (np. dzisiejszy niekompletny wiersz)
    df = df.dropna(subset=["Close"])
    if df.empty:
        return None, None
    df["RSI"]   = rsi(df["Close"])
    df["MA20"]  = df["Close"].rolling(20).mean()
    df["MA50"]  = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = macd(df["Close"])
    df["BB_mid"], df["BB_upper"], df["BB_lower"] = bollinger_bands(df["Close"])
    df["VWAP"] = compute_vwap(df)
    try:
        info = stock.info
    except Exception:
        info = {}
    return df, info


@st.cache_data(ttl=900, show_spinner=False)
def pobierz_dane(ticker: str, period: str = "1y"):
    return _pobierz_dane_core(ticker, period=period)


@st.cache_data(ttl=600, show_spinner=False)
def wyszukaj_tickery(query: str, limit: int = 8) -> list[dict]:
    """Cache'owana wyszukiwarka instrumentów (patrz stock_analyzer.search_tickers)."""
    return search_tickers(query, limit=limit)


@st.cache_data(ttl=60, show_spinner=False)
def pobierz_dane_live(ticker: str, period: str = "1y"):
    """Wersja pobierz_dane z krótkim cache (60 s) na potrzeby auto-odświeżania.

    UWAGA: Yahoo Finance i tak udostępnia dane z opóźnieniem (zwykle ~15 min),
    więc realnie nowy punkt na wykresie pojawia się co kilkanaście minut, nawet
    jeśli odświeżamy częściej. Krótki TTL zapewnia jedynie, że gdy Yahoo poda
    świeższą wartość, zobaczymy ją szybko – a nie dopiero po 15 minutach (TTL
    zwykłego pobierz_dane).
    """
    return _pobierz_dane_core(ticker, period=period)


@st.cache_data(ttl=60, show_spinner=False)
def pobierz_dane_binance(ticker: str, okres: str = "1y") -> "tuple":
    """Pobiera dane OHLCV z Binance (prawdziwe dane live) zamiast Yahoo Finance.

    Zwraca krotkę (df, None) kompatybilną z pobierz_dane() — None zamiast info,
    bo Binance nie dostarcza metadanych spółki (używane tylko do wykresu/wskaźników).

    Parametr `okres` mapowany na limit świec Binance:
    '3mo'→90, '6mo'→180, '1y'→365, '2y'→730, '5y'→1825.
    Wszystkie świece dzienne (interval='1d') — tak samo jak Yahoo.

    Fallback: gdy Binance niedostępny zwraca (None, None). Wywołujący kod
    powinien wtedy użyć Yahoo Finance jako źródła zapasowego.
    """
    limit_map = {"3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    limit = limit_map.get(okres, 365)

    klines = external_data.get_binance_klines(ticker, interval="1d", limit=limit)
    if klines is None:
        return None, None

    df = external_data.binance_klines_to_df(klines)
    if df is None or df.empty:
        return None, None

    # Wylicz te same wskaźniki co w _pobierz_dane_core, żeby wykres
    # i RSI działały identycznie niezależnie od źródła danych.
    df["RSI"]    = rsi(df["Close"])
    df["MA20"]   = df["Close"].rolling(20).mean()
    df["MA50"]   = df["Close"].rolling(50).mean()
    df["MA200"]  = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = macd(df["Close"])
    df["BB_mid"], df["BB_upper"], df["BB_lower"] = bollinger_bands(df["Close"])
    df["VWAP"]   = compute_vwap(df)

    return df, None


@st.cache_data(ttl=900, show_spinner=False)
def pobierz_analize(ticker: str) -> dict:
    return analyze_ticker(ticker)


# ── Konfiguracja interwałów intraday ──────────────────────────────────
# Każdy interwał ma: etykietę UI, interwał Yahoo, max historię Yahoo (period),
# max historię Binance (limit świec), TTL cache (sekundy).
# Opóźnienie Yahoo ~15 min niezależnie od interwału.
INTRADAY_INTERVALS = {
    "1d":  {"label": "1 dzień",    "yf": "1d",  "period": "1y",  "binance": "1d",  "limit": 365, "ttl": 900},
    "1h":  {"label": "1 godzina",  "yf": "1h",  "period": "60d", "binance": "1h",  "limit": 500, "ttl": 300},
    "30m": {"label": "30 minut",   "yf": "30m", "period": "30d", "binance": "30m", "limit": 500, "ttl": 120},
    "15m": {"label": "15 minut",   "yf": "15m", "period": "8d",  "binance": "15m", "limit": 500, "ttl": 60},
    "5m":  {"label": "5 minut",    "yf": "5m",  "period": "5d",  "binance": "5m",  "limit": 500, "ttl": 30},
    "1m":  {"label": "1 minuta",   "yf": "1m",  "period": "7d",  "binance": "1m",  "limit": 500, "ttl": 15},
}

# Maksymalna dostępna historia per interwał (info do UI)
INTRADAY_MAX_HISTORIA = {
    "1d": "lata",
    "1h": "730 dni",
    "30m": "60 dni",
    "15m": "8 dni",
    "5m": "5 dni",
    "1m": "7 dni",
}


def _dodaj_wskazniki(df: "pd.DataFrame", interval: str = "1d") -> "pd.DataFrame":
    """Dodaje wskaźniki techniczne do DataFrame OHLCV.

    Dla interwałów krótszych niż dzienny (intraday) MA50/MA200 mogą być
    bez sensu (za mało historii), ale obliczamy je i tak – puste wartości
    są po prostu NaN i nie pojawią się na wykresie.
    """
    df["RSI"]   = rsi(df["Close"])
    df["MA20"]  = df["Close"].rolling(20).mean()
    df["MA50"]  = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MACD"], df["MACD_signal"] = macd(df["Close"])
    df["BB_mid"], df["BB_upper"], df["BB_lower"] = bollinger_bands(df["Close"])
    df["VWAP"]  = compute_vwap(df)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def pobierz_dane_intraday(
    ticker: str, interval: str = "1d"
) -> "tuple":
    """Pobiera dane OHLCV dla wybranego interwału (1d / 1h / 30m / 15m / 5m / 1m).

    Routing źródeł:
    - Krypto obsługiwane przez Binance → Binance klines (brak opóźnienia!).
    - Wszystko inne → Yahoo Finance (opóźnienie ~15 min, zawsze).

    Zwraca (df, źródło_str) lub (None, None) przy błędzie.
    TTL cache: krótszy dla mniejszych interwałów (patrz INTRADAY_INTERVALS).
    """
    cfg = INTRADAY_INTERVALS.get(interval, INTRADAY_INTERVALS["1d"])

    # Krypto: użyj Binance (prawdziwy live, bez opóźnienia)
    if external_data.is_binance_supported(ticker):
        try:
            klines = external_data.get_binance_klines(
                ticker, interval=cfg["binance"], limit=cfg["limit"]
            )
            if klines:
                df = external_data.binance_klines_to_df(klines)
                if df is not None and not df.empty:
                    df = _dodaj_wskazniki(df, interval)
                    return df, "Binance (na żywo)"
        except Exception:
            pass

    # Yahoo Finance (akcje, ETF, surowce i fallback dla krypto)
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=cfg["period"], interval=cfg["yf"])
        if df is not None and not df.empty:
            df = df.dropna(subset=["Close"])
            if not df.empty:
                # Dla interwałów intraday Yahoo zwraca tz-aware index,
                # konwertujemy do UTC naive żeby uniknąć błędów Plotly.
                if hasattr(df.index, "tz") and df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df = _dodaj_wskazniki(df, interval)
                return df, f"Yahoo Finance (~15 min opóźnienia)"
    except Exception:
        pass

    return None, None


@st.cache_data(ttl=900, show_spinner=False)
def policz_historie_score(df: pd.DataFrame, dni: int = 90) -> pd.DataFrame:
    full = compute_simple_score_series(df)
    return full.tail(dni).reset_index(drop=True)


# ── Wykresy ───────────────────────────────────────────────────────────
def rysuj_wykres_ceny(
    df: pd.DataFrame,
    nazwa: str,
    tryb: str = "Linia",
    pokaz_ma20: bool = True,
    pokaz_bollinger: bool = False,
    pokaz_vwap: bool = False,
) -> go.Figure:
    """Wykres ceny: linia lub świece, z opcjonalnymi MA20, wstęgami Bollingera i VWAP.

    tryb: "Linia" lub "Świece" (candlestick OHLC).
    pokaz_ma20 / pokaz_bollinger / pokaz_vwap: nakładki włączane przez użytkownika.
    """
    fig = go.Figure()

    if pokaz_bollinger and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="Bollinger (góra)",
            line=dict(color="rgba(120,120,120,0.45)", width=1), showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="Wstęgi Bollingera",
            line=dict(color="rgba(120,120,120,0.45)", width=1),
            fill="tonexty", fillcolor="rgba(120,120,120,0.10)",
        ))

    if tryb == "Świece" and {"Open", "High", "Low"}.issubset(df.columns):
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="OHLC",
            increasing_line_color=KOLOR_DOBRY,    # #22C55E brand green
            decreasing_line_color=KOLOR_SLABY,    # #EF4444 red
        ))
        fig.update_layout(xaxis_rangeslider_visible=False)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"], name="Cena",
            line=dict(color=KOLOR_AKCENTU, width=2),  # #14B8A6 brand teal
        ))

    if pokaz_vwap and "VWAP" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["VWAP"], name="VWAP (20d)",
            line=dict(color="#E11D48", width=1.6, dash="dashdot"),
        ))

    if pokaz_ma20 and "MA20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MA20"], name="MA 20d",
            line=dict(color=KOLOR_DOBRY, width=1.3, dash="dot"),  # brand green
        ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA50"], name="MA 50d",
        line=dict(color="#F59E0B", width=1.5, dash="dot"),         # amber — czytelny
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA200"], name="MA 200d",
        line=dict(color="#7C3AED", width=1.5, dash="dot"),         # violet — czytelny
    ))

    fig.update_layout(
        height=440, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_title=None, yaxis_title="Cena", hovermode="x unified",
    )
    return apply_theme(fig)


def rysuj_wykres_rsi(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                              line=dict(color=KOLOR_AKCENTU, width=2)))  # brand teal
    fig.add_hline(y=70, line_dash="dash", line_color=KOLOR_SLABY,   annotation_text="Przegrzanie (70)")
    fig.add_hline(y=30, line_dash="dash", line_color=KOLOR_DOBRY,   annotation_text="Wyprzedanie (30)")
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10),
                       yaxis_range=[0, 100], showlegend=False)
    return apply_theme(fig)


def rysuj_wykres_scoru(components: dict) -> go.Figure:
    nazwy, wartosci, kolory = [], [], []
    for key, (val, _) in components.items():
        nazwy.append(OPISY_WSKAZNIKOW.get(key, {}).get("nazwa", key))
        wartosci.append(val)
        kolory.append(kolor_dla_score(val))
    fig = go.Figure(go.Bar(
        x=wartosci, y=nazwy, orientation="h",
        marker_color=kolory,
        text=[f"{v:.0f}" for v in wartosci], textposition="outside",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#888")
    fig.update_layout(height=max(300, 38 * len(nazwy)),
                       margin=dict(l=10, r=10, t=30, b=10),
                       xaxis_range=[0, 110], xaxis_title="Punkty (0–100)")
    return apply_theme(fig)


def rysuj_wykres_historii_score(hist_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["Date"], y=hist_df["Score"], mode="lines",
        line=dict(color=KOLOR_AKCENTU, width=2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.08)", name="Score",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="#888")
    fig.add_hline(y=70, line_dash="dot",  line_color=KOLOR_DOBRY, opacity=0.5)
    fig.add_hline(y=30, line_dash="dot",  line_color=KOLOR_SLABY, opacity=0.5)
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10),
                       yaxis_range=[0, 100], showlegend=False)
    return apply_theme(fig)


# ── UI-komponenty wielokrotnego użytku ───────────────────────────────
def score_banner(score: float, n_skladowych: int):
    """Kolorowy banner z wynikiem ogólnym — brand guide StockFlow."""
    kolor = kolor_dla_score(score)
    emoji = emoji_dla_score(score)
    interpretacja = interpret_score(score)
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {kolor}14, {kolor}08);
            border-left: 4px solid {kolor};
            border-radius: 10px;
            padding: 16px 20px;
            margin: 8px 0 18px 0;
            font-family: 'Inter', sans-serif;
        ">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <span style="font-size:1.4em">{emoji}</span>
            <span style="font-size:1.15em; font-weight:700;
                         color:{kolor};">{interpretacja}</span>
          </div>
          <span style="font-size:0.9em; opacity:0.75;">
            Wynik ogólny: <strong style="color:{KOLOR_TEKST}">{score:.0f} / 100</strong>
            &nbsp;·&nbsp; {n_skladowych} wskaźników
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_base_css():
    """Wstrzykuje globalne style CSS zgodne z brand guide StockFlow.

    Ładuje czcionkę Inter (Google Fonts), ustawia kolory i typografię
    zgodne z paleta brand (#22C55E, #14B8A6, #3B82F6), styluje metryki,
    przyciski, nagłówki i sidebar.
    Wywoływane raz per strona przez sidebar_user().
    """
    st.markdown(
        f"""
        <style>
        /* ── Inter font (brand guide: Bold, SemiBold, Regular, Light) ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

        html, body, [class*="css"], .stApp, .stMarkdown,
        .stTextInput input, .stSelectbox, .stRadio, .stCheckbox,
        button, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
            font-family: 'Inter', sans-serif !important;
        }}

        /* ── Nagłówki — brand hierarchy ── */
        h1 {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.95rem !important;
            color: {KOLOR_TEKST} !important;
            margin-bottom: .15em !important;
            letter-spacing: -0.02em;
        }}
        h2 {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            color: {KOLOR_TEKST} !important;
            letter-spacing: -0.01em;
        }}
        h3 {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            color: {KOLOR_AKCENTU} !important;
        }}

        /* ── Sidebar — brand darker background ── */
        [data-testid="stSidebar"] {{
            background-color: {KOLOR_TLO2} !important;
            border-right: 1px solid rgba(255,255,255,0.06);
        }}
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] label {{
            font-family: 'Inter', sans-serif !important;
            font-size: 0.88rem !important;
        }}

        /* ── Przyciski — brand green gradient ── */
        .stButton > button {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            border: none !important;
            background: linear-gradient(135deg, {KOLOR_DOBRY}, #16A34A) !important;
            color: #fff !important;
            transition: opacity 0.15s ease, transform 0.1s ease !important;
            letter-spacing: 0.01em;
        }}
        .stButton > button:hover {{
            opacity: 0.88 !important;
            transform: translateY(-1px) !important;
        }}
        .stButton > button:active {{
            transform: translateY(0px) !important;
        }}
        /* Przyciski secondary (outlined) — tylko border, nie gradient */
        .stButton > button[kind="secondary"] {{
            background: transparent !important;
            border: 1px solid {KOLOR_DOBRY} !important;
            color: {KOLOR_DOBRY} !important;
        }}

        /* ── Metryki jako karty ── */
        [data-testid="stMetric"] {{
            background: rgba(34, 197, 94, 0.05) !important;
            border: 1px solid rgba(34, 197, 94, 0.18) !important;
            padding: 14px 16px !important;
            border-radius: 10px !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-weight: 600 !important;
            font-size: 0.78rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            opacity: 0.65 !important;
        }}
        [data-testid="stMetricValue"] {{
            font-weight: 700 !important;
            font-size: 1.6rem !important;
            color: {KOLOR_TEKST} !important;
        }}

        /* ── Zakładki (tabs) ── */
        button[data-baseweb="tab"] {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            font-size: 0.92rem !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {KOLOR_DOBRY} !important;
            font-weight: 600 !important;
        }}

        /* ── Tabele ── */
        [data-testid="stDataFrame"] {{
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
        }}

        /* ── Inputy i selectboxy ── */
        .stTextInput input, .stSelectbox select,
        [data-baseweb="input"] input,
        [data-baseweb="select"] {{
            font-family: 'Inter', sans-serif !important;
            border-radius: 8px !important;
            border-color: rgba(255,255,255,0.12) !important;
        }}
        .stTextInput input:focus,
        [data-baseweb="input"] input:focus {{
            border-color: {KOLOR_DOBRY} !important;
            box-shadow: 0 0 0 2px rgba(34,197,94,0.18) !important;
        }}

        /* ── Alerty / info boxy ── */
        [data-testid="stAlert"] {{
            border-radius: 10px !important;
            border-width: 1px !important;
        }}

        /* ── Divider ── */
        hr {{
            border-color: rgba(255,255,255,0.08) !important;
            margin: 1em 0 !important;
        }}

        /* ── Scrollbar — subtelny brand styl ── */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: {KOLOR_TLO2}; }}
        ::-webkit-scrollbar-thumb {{
            background: rgba(34,197,94,0.35);
            border-radius: 3px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(34,197,94,0.6);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(tytul: str, podtytul: str = "", ikona: str = ""):
    """Spójny nagłówek strony zgodny z brand guide StockFlow."""
    naglowek = f"{ikona} {tytul}".strip()
    st.markdown(
        f"""
        <div style="margin-bottom: 0.5rem;">
          <h1 style="
            font-family: Inter, sans-serif;
            font-weight: 700;
            font-size: 1.95rem;
            color: {KOLOR_TEKST};
            margin: 0 0 4px 0;
            letter-spacing: -0.02em;
          ">{naglowek}</h1>
          {"" if not podtytul else
            f'<p style="font-family:Inter,sans-serif; font-size:0.9rem; '
            f'color:{KOLOR_NEUTRALNY}; margin:0 0 8px 0;">{podtytul}</p>'
          }
          <div style="height:3px; width:48px;
            background:linear-gradient(90deg,{KOLOR_DOBRY},{KOLOR_AKCENTU});
            border-radius:2px; margin-bottom:12px;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_pill(score: float) -> str:
    """Zwraca inline'owy, kolorowy 'pill' z wynikiem (HTML) do osadzenia w markdown."""
    kolor = kolor_dla_score(score)
    return (
        f'<span style="background:{kolor}1A; color:{kolor}; '
        f'padding:3px 12px; border-radius:999px; font-weight:600; '
        f'font-size:0.88em; font-family:Inter,sans-serif; '
        f'white-space:nowrap; border:1px solid {kolor}40">'
        f'{score:.0f}/100</span>'
    )


def karta_instrumentu(res: dict, key_prefix: str, user_id: str, db_mod):
    """Jeden wiersz-karta dla ETF/surowca/spółki wzrostowej."""
    import database as db
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    ticker = res["ticker"]
    with col1:
        st.markdown(f"**{res['name']}** `{ticker}`")
        meta = res.get("sector") or res.get("category") or res.get("asset_type_label", "")
        if meta:
            st.caption(f"🏷 {meta}")
        if res.get("opis"):
            st.caption(res["opis"])
    with col2:
        st.metric("Cena", f"{res['price']} {res['currency']}")
    with col3:
        st.metric("Wynik", badge_score(res["score"]),
                  delta=interpret_score(res["score"]), delta_color="off",
                  help=LEGENDA_SCORE)
    with col4:
        st.write("")
        if st.button("⭐ Watchlist", key=f"{key_prefix}_{ticker}", use_container_width=True):
            db_mod.add_to_watchlist(ticker, user_id)
            db_mod.update_watchlist_score(ticker, res["score"], user_id)
            st.success(f"Dodano {ticker}!")
    st.divider()


def ticker_search_widget(
    label: str = "Wyszukaj instrument",
    key: str = "ticker_search",
    default_ticker: str = "AAPL",
) -> str:
    """Pole wyszukiwania instrumentu po nazwie lub symbolu.

    Użytkownik wpisuje np. "apple" lub "AAPL"; widget odpytuje Yahoo Finance
    i pokazuje listę dopasowań. Zwraca wybrany symbol. Wybór jest trzymany
    w st.session_state, więc przetrwa rerun.
    """
    selected_key = f"{key}__selected"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = default_ticker

    query = st.text_input(
        label,
        key=f"{key}__query",
        placeholder="np. apple, CD Projekt, AAPL, BTC…",
        help="Wpisz nazwę firmy lub symbol. Wyniki pochodzą z Yahoo Finance.",
    )

    if query and query.strip():
        wyniki = wyszukaj_tickery(query.strip())
        if wyniki:
            etykiety = {
                f"{r['symbol']} — {r['name']}"
                + (f" · {r['exchange']}" if r["exchange"] else ""): r["symbol"]
                for r in wyniki
            }
            wybor = st.selectbox("Dopasowania", list(etykiety.keys()), key=f"{key}__select")
            if wybor:
                st.session_state[selected_key] = etykiety[wybor]
        else:
            st.caption("Brak wyników – spróbuj innej frazy lub wpisz symbol wprost.")

    return st.session_state[selected_key]


def sidebar_user(key: str = "user_id") -> str:
    """Renderuje pole użytkownika w sidebarze i zwraca user_id.

    Przy okazji wstrzykuje wspólne style CSS (raz na stronę) i logo StockFlow.
    """
    inject_base_css()
    with st.sidebar:
        # Logo tekstowe StockFlow (do czasu dodania pliku graficznego)
        st.markdown(
            f"""
            <div style="padding: 12px 0 18px 0; text-align: center;">
              <span style="
                font-family: Inter, sans-serif;
                font-size: 1.55rem;
                font-weight: 700;
                letter-spacing: -0.02em;
              ">
                <span style="color:{KOLOR_DOBRY};">Stock</span><span style="color:{KOLOR_AKCENTU};">Flow</span>
              </span>
              <div style="font-size:0.68rem; opacity:0.45; margin-top:2px;
                          font-family:Inter,sans-serif; letter-spacing:0.04em;">
                ANALITYKA RYNKOWA
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_input(
            "👤 Twoja nazwa",
            value="default",
            key=key,
            help="Oddziela watchlisty, portfolio i ustawienia między użytkownikami. "
                 "Nie jest zabezpieczone hasłem – tylko etykieta.",
        )
    return (st.session_state.get(key) or "default").strip() or "default"


def sidebar_legenda():
    with st.sidebar:
        st.divider()
        st.caption(
            "🟢 **60–100**: sygnały pozytywne  \n"
            "⚪ **40–60**: brak wyraźnego sygnału  \n"
            "🔴 **0–40**: sygnały negatywne  \n\n"
            "Wynik **nie przewiduje** przyszłości."
        )


def footer(pokaz_feedback: bool = True):
    st.divider()
    st.caption(DISCLAIMER)
    if pokaz_feedback:
        st.caption(
            f"💬 Wersja testowa – [zgłoś uwagę lub błąd]({FEEDBACK_URL}) "
            "· ℹ️ więcej w zakładce „O aplikacji”."
        )
    st.markdown(
        f"<p style='font-family:Inter,sans-serif; font-size:0.78rem; "
        f"opacity:0.45; text-align:center; margin-top:6px;'>"
        f"<span style='color:{KOLOR_DOBRY}; font-weight:600;'>Stock</span>"
        f"<span style='color:{KOLOR_AKCENTU}; font-weight:600;'>Flow</span>"
        f" \u00a0·\u00a0 v{APP_VERSION}"
        f"</p>",
        unsafe_allow_html=True,
    )


def banner_dane_niedostepne():
    """Globalny baner, gdy Yahoo Finance nie odpowiada.

    Zamiast pokazywać surowe wyjątki, wołaj to gdy pobranie danych zwróci
    pustkę/błąd dla instrumentu, który powinien działać.
    """
    st.error(
        "📡 **Dane chwilowo niedostępne.** Yahoo Finance może mieć przejściowy "
        "problem lub ograniczać ruch. Odczekaj chwilę i odśwież stronę "
        "(czasem pomaga ponowna próba za 1–2 minuty)."
    )


def beta_banner():
    """Baner informujący, że to wersja testowa z ulotnymi danymi.

    Streamlit Cloud kasuje dysk przy restarcie/redeploy, więc watchlisty,
    portfolio i ustawienia mogą zniknąć. Wyświetlamy to wprost, żeby testerzy
    nie zgłaszali tego jako błąd.
    """
    st.warning(
        "🧪 **Wersja testowa (beta).** To narzędzie edukacyjne, **nie** porada "
        "inwestycyjna. Dane mogą się okresowo resetować (watchlista, portfolio, "
        "ustawienia) – to normalne dla wersji testowej. Dziękujemy za testy!"
    )
