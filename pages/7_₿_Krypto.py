"""
Kryptowaluty
=============
Przegląd popularnych kryptowalut z oceną techniczną (score). Krypto nie ma
fundamentów spółki, więc score opiera się wyłącznie na analizie technicznej.
"""
import streamlit as st
import pandas as pd

from common import (
    LEGENDA_SCORE,
    badge_score,
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
from tickers import KRYPTO_LIST
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("₿ Kryptowaluty")
st.warning(
    "⚠️ **Kryptowaluty są wyjątkowo zmienne i ryzykowne.** Score opiera się "
    "wyłącznie na analizie technicznej (trend, RSI, MACD, zmienność, momentum) "
    "– kryptowaluty nie mają fundamentów spółki (P/E, dywidendy, przychodów). "
    "Wynik **nie jest** prognozą ani rekomendacją."
)
st.divider()

# ── Pobranie i analiza wszystkich pozycji z listy ────────────────────
wyniki = []
with st.spinner("Analiza kryptowalut…"):
    for nazwa, (ticker, opis) in KRYPTO_LIST.items():
        try:
            res = pobierz_analize(ticker)
        except Exception:
            continue
        if "error" in res:
            continue
        # Pomiń pozycje bez sensownej ceny (Yahoo czasem zwraca 0/NaN dla krypto).
        cena = res.get("price")
        if cena is None or cena <= 0:
            continue
        wyniki.append({
            "nazwa": nazwa,
            "ticker": ticker,
            "opis": opis,
            "name": res["name"],
            "price": res["price"],
            "currency": res["currency"],
            "score": res["total_score"],
        })

if not wyniki:
    st.error(
        "Nie udało się pobrać danych dla żadnej kryptowaluty. "
        "Yahoo Finance może mieć chwilowy problem – spróbuj ponownie za chwilę."
    )
    st.stop()

wyniki.sort(key=lambda w: w["score"], reverse=True)

# ── Tabela zbiorcza ──────────────────────────────────────────────────
df_show = pd.DataFrame([{
    "Nazwa": w["nazwa"].split(" (")[0],
    "Ticker": w["ticker"],
    "Cena (USD)": w["price"],
    "Wynik": w["score"],
    "Ocena": interpret_score(w["score"]),
} for w in wyniki])

st.dataframe(
    df_show.style.background_gradient(subset=["Wynik"], cmap="RdYlGn", vmin=0, vmax=100),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Karty szczegółowe ────────────────────────────────────────────────
for w in wyniki:
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"**{w['name']}** `{w['ticker']}`")
        st.caption(w["opis"])
    with col2:
        st.metric(
            "Cena",
            f"${w['price']:,.2f}" if w["currency"] == "USD"
            else f"{w['price']} {w['currency']}",
        )
    with col3:
        st.metric("Wynik", badge_score(w["score"]),
                  delta=interpret_score(w["score"]), delta_color="off",
                  help=LEGENDA_SCORE)
    with col4:
        st.write("")
        if st.button("⭐ Watchlist", key=f"krypto_wl_{w['ticker']}", use_container_width=True):
            db.add_to_watchlist(w["ticker"], user_id)
            db.update_watchlist_score(w["ticker"], w["score"], user_id)
            st.success(f"Dodano {w['ticker']}!")
    st.divider()

st.caption(
    "💡 Krypto i tradycyjne aktywa (akcje, obligacje) mają często niską "
    "lub zmienną korelację – kryptowaluty bywają używane jako element "
    "dywersyfikacji, choć przy globalnym 'risk-off' potrafią spadać razem "
    "z akcjami."
)

footer()
