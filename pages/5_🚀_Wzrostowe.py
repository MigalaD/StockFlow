# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Spółki wzrostowe
"""
import streamlit as st
from common import (
    section_header, empty_state,
    LEGENDA_SCORE,
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
from tickers import SPOLKI_WZROSTOWE
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("🚀 Spółki wzrostowe")

st.info(
    "ℹ️ **Ważne wyjaśnienie**: to NIE są prywatne startupy. Dane "
    "finansowe prywatnych startupów (przed IPO) nie są publicznie "
    "dostępne - wymagają płatnych baz typu Crunchbase/PitchBook, do "
    "których ta aplikacja nie ma dostępu. Poniższa lista to "
    "**spółki już notowane na giełdzie**, często po niedawnym IPO "
    "lub w fazie szybkiego wzrostu - dlatego są ciekawe do "
    "śledzenia, ale zwykle też **bardziej zmienne i ryzykowne** niż "
    "duże, ugruntowane firmy."
)

st.markdown(
    "Lista jest edytowalna w pliku `tickers.py` (`SPOLKI_WZROSTOWE`) - "
    "dodaj własne spółki, które chcesz śledzić."
)

with st.spinner("Sprawdzanie spółek wzrostowych..."):
    wyniki_wzrost = []
    for nazwa, (tckr, opis) in SPOLKI_WZROSTOWE.items():
        try:
            res = pobierz_analize(tckr)
        except Exception:
            continue
        if "error" in res:
            continue
        if res.get("price") is None or res["price"] <= 0:
            continue
        wyniki_wzrost.append({
            "nazwa": nazwa, "ticker": tckr, "opis": opis,
            "score": res["total_score"], "price": res["price"],
            "currency": res["currency"], "name": res["name"],
            "sector": res.get("sector", "Nieznany"),
        })

if not wyniki_wzrost:
    st.error("Nie udało się pobrać danych dla żadnej spółki z listy.")
    st.stop()

wyniki_wzrost.sort(key=lambda x: -x["score"])

for w in wyniki_wzrost:
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"**{w['name']}** ({w['ticker']})")
        st.caption(f"🏷️ {w['sector']}")
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
        if st.button("⭐ Do watchlist", key=f"wl_{w['ticker']}"):
            db.add_to_watchlist(w["ticker"], user_id)
            db.update_watchlist_score(w["ticker"], w["score"], user_id)
            st.success(f"Dodano {w['ticker']} do watchlist!")
    st.divider()

st.caption(
    "⚠️ Spółki wzrostowe / po niedawnym IPO często mają wysoką "
    "zmienność, krótszą historię finansową i wyższe ryzyko niż duże, "
    "ugruntowane firmy. Wynik liczony jest tą samą metodologią co "
    "dla innych spółek, ale przy krótszej historii niektóre "
    "wskaźniki (np. trend 200-dniowy) mogą być mniej wiarygodne."
)



footer()
