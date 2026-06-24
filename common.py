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
KOLOR_DOBRY     = "#1a9850"
KOLOR_NEUTRALNY = "#999999"
KOLOR_SLABY     = "#d73027"
KOLOR_AKCENTU   = "#2563eb"

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
    fig.update_layout(
        template=get_plotly_template(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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


@st.cache_data(ttl=900, show_spinner=False)
def pobierz_analize(ticker: str) -> dict:
    return analyze_ticker(ticker)


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
            increasing_line_color=KOLOR_DOBRY,
            decreasing_line_color=KOLOR_SLABY,
        ))
        fig.update_layout(xaxis_rangeslider_visible=False)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"], name="Cena",
            line=dict(color=KOLOR_AKCENTU, width=2),
        ))

    if pokaz_vwap and "VWAP" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["VWAP"], name="VWAP (20d)",
            line=dict(color="#e11d48", width=1.6, dash="dashdot"),
        ))

    if pokaz_ma20 and "MA20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MA20"], name="MA 20d",
            line=dict(color="#10b981", width=1.3, dash="dot"),
        ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA50"], name="MA 50d",
        line=dict(color="#f59e0b", width=1.5, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA200"], name="MA 200d",
        line=dict(color="#7c3aed", width=1.5, dash="dot"),
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
                              line=dict(color="#0891b2", width=2)))
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
    """Kolorowy banner z wynikiem ogólnym."""
    kolor = kolor_dla_score(score)
    emoji = emoji_dla_score(score)
    st.markdown(
        f"""
        <div style="
            background:{kolor}18;
            border-left:5px solid {kolor};
            padding:14px 18px;
            border-radius:8px;
            margin:8px 0 18px 0;
        ">
          <span style="font-size:1.25em">{emoji} <strong>{interpret_score(score)}</strong></span><br>
          <span style="opacity:.8">
            Wynik ogólny: <strong>{score:.0f}/100</strong>
            &nbsp;(na podstawie {n_skladowych} wskaźników)
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_base_css():
    """Wstrzykuje wspólne style CSS dla spójnego, dopracowanego wyglądu.

    Wywoływane raz na każdej stronie (tuż po sidebarze). Poprawia odstępy,
    zaokrąglenia metryk, wygląd przycisków i nagłówków – tak, by całość
    sprawiała wrażenie spójnego produktu, a nie zlepka domyślnych widżetów.
    """
    st.markdown(
        """
        <style>
        /* Metryki jako "karty" z delikatnym tłem i obramowaniem */
        [data-testid="stMetric"] {
            background: rgba(128,128,128,0.06);
            border: 1px solid rgba(128,128,128,0.15);
            padding: 14px 16px;
            border-radius: 10px;
        }
        [data-testid="stMetricLabel"] { opacity: .75; }
        /* Przyciski: pełna szerokość czytelniej, lekkie zaokrąglenie */
        .stButton > button { border-radius: 8px; font-weight: 500; }
        /* Nagłówek strony – mniejszy margines dolny */
        h1 { margin-bottom: .2em; }
        /* Zakładki – trochę więcej oddechu */
        button[data-baseweb="tab"] { font-size: 0.95rem; }
        /* Tabele – delikatne zaokrąglenie rogów */
        [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(tytul: str, podtytul: str = "", ikona: str = ""):
    """Spójny nagłówek strony: tytuł + opcjonalny podtytuł i ikona.

    Używaj na górze każdej strony zamiast samego st.title(), żeby wszystkie
    strony miały identyczny rytm wizualny.
    """
    naglowek = f"{ikona} {tytul}".strip()
    st.title(naglowek)
    if podtytul:
        st.caption(podtytul)
    st.divider()


def score_pill(score: float) -> str:
    """Zwraca inline'owy, kolorowy "pill" z wynikiem (HTML) do osadzenia w markdown.

    Przykład: st.markdown(score_pill(72), unsafe_allow_html=True)
    """
    kolor = kolor_dla_score(score)
    return (
        f'<span style="background:{kolor}22;color:{kolor};'
        f'padding:2px 10px;border-radius:999px;font-weight:600;'
        f'font-size:0.9em;white-space:nowrap">{score:.0f}/100</span>'
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

    Przy okazji wstrzykuje wspólne style CSS (raz na stronę), dzięki czemu
    każda strona ma spójny, dopracowany wygląd bez powielania kodu.
    """
    inject_base_css()
    with st.sidebar:
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
    st.caption(f"Analizator Spółek · wersja {APP_VERSION}")


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
