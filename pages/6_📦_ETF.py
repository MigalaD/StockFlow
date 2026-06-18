"""
ETF i Surowce
"""
import streamlit as st
from common import (
    LEGENDA_SCORE,
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
from tickers import ETF_LIST, KOMODITY_LIST
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("📦 ETF i Surowce")

st.info(
    "ℹ️ ETF-y i surowce **nie mają fundamentów spółek** (P/E, "
    "dywidenda, dług, wzrost przychodów). Dlatego dla tych instrumentów "
    "te wskaźniki są **wyłączone**, a wagi pozostałych (analiza "
    "techniczna, sentyment, dla ETF-ów też wycena/dywidenda jeśli "
    "dostępne) są przeliczone tak, by sumowały się do 100%. Szczegóły "
    "w zakładce 'Szczegóły wyniku' przy analizie konkretnego "
    "instrumentu."
)

podsekcja = st.radio(
    "Co chcesz przeglądać?",
    ["📊 ETF-y", "🛢️ Surowce"],
    horizontal=True,
)

lista = ETF_LIST if podsekcja == "📊 ETF-y" else KOMODITY_LIST

#st.markdown(
#    "Lista jest edytowalna w pliku `tickers.py` "
#    f"(`{'ETF_LIST' if podsekcja == '📊 ETF-y' else 'KOMODITY_LIST'}`)."
#)

with st.spinner("Sprawdzanie..."):
    wyniki_etf = []
    for nazwa, (tckr, opis) in lista.items():
        try:
            res = pobierz_analize(tckr)
        except Exception:
            continue
        if "error" in res:
            continue
        if res.get("price") is None or res["price"] <= 0:
            continue
        wyniki_etf.append({
            "nazwa": nazwa, "ticker": tckr, "opis": opis,
            "score": res["total_score"], "price": res["price"],
            "currency": res["currency"], "name": res["name"],
            "asset_type_label": res.get("asset_type_label", "Inny instrument"),
            "category": res.get("category"),
        })

if not wyniki_etf:
    st.error("Nie udało się pobrać danych dla żadnej pozycji z listy.")
    st.stop()

wyniki_etf.sort(key=lambda x: -x["score"])

for w in wyniki_etf:
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"**{w['name']}** ({w['ticker']})")
        badge = w["asset_type_label"]
        if w.get("category"):
            badge += f" • {w['category']}"
        st.caption(f"🏷️ {badge}")
        st.caption(w["opis"])
    with col2:
        st.metric("Cena", f"{w['price']} {w['currency']}")
    with col3:
        st.metric(
            "Wynik", f"{w['score']:.0f}/100",
            delta=interpret_score(w["score"]), delta_color="off",
            help=LEGENDA_SCORE,
        )
    with col4:
        st.write("")
        st.write("")
        if st.button("⭐ Do watchlist", key=f"wl_etf_{w['ticker']}"):
            db.add_to_watchlist(w["ticker"], user_id)
            db.update_watchlist_score(w["ticker"], w["score"], user_id)
            st.success(f"Dodano {w['ticker']} do watchlist!")
    st.divider()

if podsekcja == "🛢️ Surowce":
    st.caption(
        "💡 Surowce często mają **niską lub ujemną korelację z akcjami** "
        "(sprawdź w zakładce 'Analiza jednej spółki' → 'Dodatkowy "
        "kontekst' → Beta/korelacja z S&P 500) - dlatego bywają używane "
        "jako element dywersyfikacji portfela, niezależnie od tego, "
        "czy ich własny 'score' jest wysoki czy niski."
    )
else:
    st.caption(
        "💡 ETF-y branżowe/regionalne (np. XLE, VWO) bywają bardziej "
        "zmienne niż szerokie indeksy (SPY, VTI) - mniejsza "
        "dywersyfikacja wewnątrz funduszu."
    )



footer()
