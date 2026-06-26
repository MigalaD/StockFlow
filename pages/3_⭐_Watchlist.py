# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Watchlist
"""
import streamlit as st
from common import (
    LEGENDA_SCORE, KOLOR_DOBRY, KOLOR_SLABY, KOLOR_NEUTRALNY,
    emoji_dla_score, kolor_dla_score,
    section_header, empty_state, karta_watchlist,
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
from telegram_alerts import default_thresholds
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("⭐ Watchlist")

with st.form("dodaj_watchlist", clear_on_submit=True):
    col_a, col_b = st.columns([3, 1])
    with col_a:
        nowy_ticker = st.text_input(
            "Dodaj spółkę do watchlist (symbol)",
            placeholder="np. AAPL, CDR.WA",
            label_visibility="collapsed",
        )
    with col_b:
        dodaj = st.form_submit_button("➕ Dodaj", use_container_width=True)

if dodaj and nowy_ticker.strip():
    from stock_analyzer import validate_ticker
    with st.spinner(f"Sprawdzanie symbolu {nowy_ticker.strip().upper()}…"):
        check = validate_ticker(nowy_ticker)
    if check["valid"]:
        db.add_to_watchlist(check["ticker"], user_id)
        st.success(
            f"Dodano {check['ticker']} ({check['name']}) do watchlist – "
            f"ostatnia cena {check['price']}."
        )
    else:
        st.error(f"Nie dodano {nowy_ticker.strip().upper()}: {check['reason']}")

watchlist = db.get_watchlist(user_id)

if not watchlist:
    empty_state(
        "⭐",
        "Watchlist jest pusta",
        "Dodaj spółkę powyżej lub użyj przycisku '⭐ Dodaj do watchlist' "
        "przy analizie dowolnej spółki.",
    )
    st.stop()

default_high, default_low = default_thresholds()

section_header("Obserwowane instrumenty", "📋",
             "Kliknij symbol aby przejść do szczegółowej analizy")

col_l, col_r = st.columns(2)
col_idx = 0

for entry in watchlist:
    ticker = entry["ticker"]
    try:
        wynik = pobierz_analize(ticker)
    except Exception:
        wynik = {"error": "błąd pobierania"}

    if "error" in wynik:
        with (col_l if col_idx % 2 == 0 else col_r):
            st.warning(f"{ticker}: błąd pobierania danych", icon="⚠️")
        col_idx += 1
        continue

    nowy   = wynik["total_score"]
    stary  = entry.get("last_score")
    delta  = (nowy - stary) if stary is not None else None

    with (col_l if col_idx % 2 == 0 else col_r):
        karta_watchlist(
            ticker=ticker,
            name=wynik["name"],
            score=nowy,
            score_st=wynik.get("score_st"),
            price=wynik["price"],
            currency=wynik["currency"],
            delta=delta,
            sektor=wynik.get("sector", ""),
        )
        # Alerty i usuwanie w expanderze (żeby nie zaśmiecać karty)
        with st.expander(f"⚙️ Alerty i opcje — {ticker}", expanded=False):
            alert_high = entry.get("alert_high") or default_high
            alert_low  = entry.get("alert_low")  or default_low
            a1, a2 = st.columns(2)
            with a1:
                nowy_high = st.number_input(
                    "Alert wysoki (score >)", min_value=0, max_value=100,
                    value=int(alert_high), step=5,
                    key=f"ah_{ticker}",
                    help="Powiadomienie gdy score przekroczy ten próg",
                )
            with a2:
                nowy_low = st.number_input(
                    "Alert niski (score <)", min_value=0, max_value=100,
                    value=int(alert_low), step=5,
                    key=f"al_{ticker}",
                    help="Powiadomienie gdy score spadnie poniżej tego progu",
                )
            alert_crossover = bool(entry.get("alert_crossover", 0))
            nowy_crossover = st.checkbox(
                "Alert crossover MA (złoty/krzyż śmierci)",
                value=alert_crossover, key=f"ac_{ticker}",
            )
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("💾 Zapisz alerty", key=f"save_{ticker}",
                             use_container_width=True):
                    db.update_watchlist_score(ticker, nowy, user_id)
                    db.set_watchlist_alerts(ticker, nowy_high, nowy_low,
                                            nowy_crossover, user_id)
                    st.success("Zapisano!", icon="✓")
            with bc2:
                if st.button("🗑️ Usuń z watchlisty", key=f"rm_{ticker}",
                             use_container_width=True):
                    db.remove_from_watchlist(ticker, user_id)
                    st.rerun()
    col_idx += 1

st.caption(
    "ℹ️ Zmiany score są liczone od ostatniej wizyty na tej stronie. "
    "Aby śledzić zmiany automatycznie, skonfiguruj `scheduler.py` "
    "(zakładka 'Ustawienia')."
)


footer()
