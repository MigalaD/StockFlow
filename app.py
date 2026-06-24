# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
app.py – punkt startowy aplikacji
===================================
Uruchomienie: streamlit run app.py

Streamlit automatycznie wykrywa pliki w folderze pages/ i tworzy
nawigację. Ten plik pełni rolę strony głównej (Start).
"""

import streamlit as st
import yfinance as yf

from common import (
    pobierz_analize, emoji_dla_score, badge_score, LEGENDA_SCORE,
    KOLOR_DOBRY, KOLOR_SLABY, footer, sidebar_user, sidebar_legenda,
    beta_banner,
)
import database as db

# ── Konfiguracja strony ───────────────────────────────────────────────
st.set_page_config(
    page_title="Analizator Spółek",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────
user_id = sidebar_user()
sidebar_legenda()

# ── Nagłówek ─────────────────────────────────────────────────────────
st.title("📊 Analizator Spółek")
st.caption(
    "Narzędzie do analizy technicznej i fundamentalnej spółek, ETF-ów, "
    "kryptowalut i surowców. **Nie jest to porada inwestycyjna.**"
)
beta_banner()
st.divider()

# ── Szybka nawigacja ─────────────────────────────────────────────────
st.markdown(f"#### 👋 Witaj, **{user_id}**")
st.markdown(
    "**Szybka nawigacja** – wybierz stronę z menu po lewej stronie:  \n"
    "📈 **Analiza spółki** &nbsp;·&nbsp; "
    "💼 **Portfolio** &nbsp;·&nbsp; "
    "🔍 **Skaner rynku** &nbsp;·&nbsp; "
    "🧪 **Backtest** &nbsp;·&nbsp; "
    "₿ **Krypto** &nbsp;·&nbsp; "
    "📦 **ETF i Surowce**"
)
st.divider()


# ── VIX – kontekst makro ─────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def get_vix():
    try:
        vix = yf.Ticker("^VIX")
        df = vix.history(period="5d")
        if df.empty:
            return None, None
        current = float(df["Close"].iloc[-1])
        prev    = float(df["Close"].iloc[-2]) if len(df) > 1 else current
        return current, current - prev
    except Exception:
        return None, None


vix_val, vix_delta = get_vix()

with st.container():
    col_vix, col_spacer = st.columns([2, 3])
    with col_vix:
        if vix_val is not None:
            if vix_val < 15:
                vix_label, vix_color = "Spokój (niski strach)", KOLOR_DOBRY
            elif vix_val < 25:
                vix_label, vix_color = "Normalny poziom zmienności", "#f59e0b"
            elif vix_val < 35:
                vix_label, vix_color = "Podwyższona zmienność / niepewność", "#e07800"
            else:
                vix_label, vix_color = "Wysoki strach / panika rynkowa", KOLOR_SLABY

            st.markdown(
                f"""
                <div style="background:{vix_color}18;border-left:4px solid {vix_color};
                            padding:12px 16px;border-radius:6px;margin-bottom:12px">
                  <span style="font-size:.8em;opacity:.7">VIX (indeks strachu)</span><br>
                  <span style="font-size:1.6em;font-weight:700">{vix_val:.1f}</span>
                  <span style="font-size:.9em;margin-left:8px">{vix_delta:+.2f}</span>
                  <br><span style="font-size:.85em">{vix_label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                "VIX mierzy oczekiwaną zmienność S&P 500 w ciągu 30 dni. "
                "Wysokie wartości sygnalizują strach i niepewność na rynku – "
                "wyniki score mogą być wtedy bardziej niestabilne niż zwykle."
            )
        else:
            st.info("Nie udało się pobrać VIX.")


st.divider()

# ── Watchlist ─────────────────────────────────────────────────────────
watchlist = db.get_watchlist(user_id)
st.markdown("#### ⭐ Twoja watchlist")

if not watchlist:
    # Onboarding: nowy użytkownik widzi pusty ekran - pomóżmy mu zacząć.
    st.markdown(
        "👋 **Wygląda na to, że dopiero zaczynasz!** Wynik (score) to liczba "
        "**0–100** podsumowująca sygnały techniczne i fundamentalne instrumentu "
        "– 🟢 wysoki = więcej sygnałów pozytywnych, 🔴 niski = negatywnych. "
        "**To nie jest porada inwestycyjna.**"
    )
    st.markdown("Dodaj kilka spółek na start, aby zobaczyć, jak to działa:")

    startery = {
        "🍎 Apple": "AAPL",
        "🪟 Microsoft": "MSFT",
        "🔍 Alphabet (Google)": "GOOGL",
        "🎮 CD Projekt": "CDR.WA",
        "🏦 PKO BP": "PKO.WA",
        "₿ Bitcoin": "BTC-USD",
    }
    cols = st.columns(3)
    for i, (label, tk) in enumerate(startery.items()):
        with cols[i % 3]:
            if st.button(label, key=f"onb_{tk}", use_container_width=True):
                db.add_to_watchlist(tk, user_id)
                st.success(f"Dodano {tk}!")
                st.rerun()

    st.caption(
        "Możesz też wpisać dowolny symbol w zakładce **⭐ Watchlist**, "
        "albo przejść od razu do **📈 Analiza**. Więcej o aplikacji: zakładka "
        "**ℹ️ O aplikacji**."
    )
else:
    zmiany = []
    with st.spinner("Sprawdzanie watchlist…"):
        for entry in watchlist:
            ticker = entry["ticker"]
            try:
                wynik = pobierz_analize(ticker)
            except Exception:
                continue
            if "error" in wynik:
                continue
            nowy   = wynik["total_score"]
            stary  = entry.get("last_score")
            delta  = (nowy - stary) if stary is not None else 0.0
            zmiany.append({"ticker": ticker, "name": wynik["name"],
                            "score": nowy, "delta": delta,
                            "price": wynik["price"], "currency": wynik["currency"]})

    if zmiany:
        zmiany.sort(key=lambda x: -abs(x["delta"]))

        # metryki top-4
        cols = st.columns(min(len(zmiany), 4))
        for i, z in enumerate(zmiany[:4]):
            with cols[i]:
                st.metric(
                    f"{z['ticker']}",
                    f"{z['score']:.0f}/100",
                    delta=f"{z['delta']:+.1f}" if z["delta"] else None,
                    help=LEGENDA_SCORE,
                )

        # zmiany ≥ 3 pkt
        duze = [z for z in zmiany if abs(z["delta"]) >= 3][:3]
        if duze:
            st.markdown("**Największe zmiany od ostatniej wizyty:**")
            for z in duze:
                ikona = "📈" if z["delta"] > 0 else "📉"
                st.markdown(
                    f"- {emoji_dla_score(z['score'])} **{z['ticker']}** "
                    f"({z['name']}) {ikona} {z['delta']:+.1f} pkt → {z['score']:.0f}/100"
                )

st.divider()

# ── Ostatni skan ──────────────────────────────────────────────────────
st.markdown("#### 🔍 Ostatni skan rynku")
last_scan = db.get_last_scan_time()
if not last_scan:
    st.info("Skan rynku nie był jeszcze uruchamiany. Przejdź do strony 🔍 Skaner.")
else:
    st.caption(f"Ostatni skan: {last_scan[:19].replace('T', ' ')}")
    results = db.get_scan_results()
    if results:
        col_top, col_bot = st.columns(2)
        with col_top:
            st.markdown("🟢 **Top 5**")
            for r in results[:5]:
                st.markdown(f"- **{r['ticker']}** ({r['name']}) — {r['score']:.0f}/100")
        with col_bot:
            st.markdown("🔴 **Bottom 5**")
            for r in results[-5:]:
                st.markdown(f"- **{r['ticker']}** ({r['name']}) — {r['score']:.0f}/100")

footer()
