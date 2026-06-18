"""
Watchlist
"""
import streamlit as st
from common import (
    LEGENDA_SCORE,
    emoji_dla_score,
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
st.markdown(
    "Tutaj znajdziesz spółki, które obserwujesz. Wynik jest "
    "przeliczany przy każdym wejściu na tę stronę, a poniżej "
    "widzisz, jak zmienił się od ostatniego sprawdzenia. Możesz "
    "też ustawić własne progi alertów Telegram dla każdej spółki "
    "(wymaga konfiguracji w zakładce 'Ustawienia')."
)

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
    st.info(
        "Watchlist jest pusta. Dodaj spółkę powyżej, albo użyj "
        "przycisku '⭐ Dodaj do watchlist' przy analizie jednej spółki."
    )
    st.stop()

default_high, default_low = default_thresholds()
st.divider()

for entry in watchlist:
    ticker = entry["ticker"]
    try:
        wynik = pobierz_analize(ticker)
    except Exception:
        wynik = {"error": "błąd pobierania"}

    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

    if "error" in wynik:
        with col1:
            st.markdown(f"**{ticker}**")
            st.caption("Nie udało się pobrać danych")
        with col5:
            if st.button("🗑️ Usuń", key=f"del_{ticker}"):
                db.remove_from_watchlist(ticker, user_id)
                st.rerun()
        st.divider()
        continue

    nowy_score = wynik["total_score"]
    stary_score = entry.get("last_score")
    zmiana = (nowy_score - stary_score) if stary_score is not None else None

    with col1:
        st.markdown(f"**{wynik['name']}** ({ticker})")
        st.caption(f"🏷️ {wynik.get('sector', 'Nieznany')}")
    with col2:
        st.metric("Cena", f"{wynik['price']} {wynik['currency']}")
    with col3:
        st.metric(
            "Wynik", f"{nowy_score:.0f}/100",
            delta=(f"{zmiana:+.1f}" if zmiana is not None else None),
            help=LEGENDA_SCORE,
        )
    with col4:
        st.markdown(
            f"<div style='padding-top: 10px;'>{emoji_dla_score(nowy_score)} "
            f"{interpret_score(nowy_score)}</div>",
            unsafe_allow_html=True,
        )
    with col5:
        if st.button("🗑️ Usuń", key=f"del_{ticker}"):
            db.remove_from_watchlist(ticker, user_id)
            st.rerun()

    with st.expander(f"🔔 Progi alertów Telegram dla {ticker}"):
        col_h, col_l, col_save = st.columns([1, 1, 1])
        cur_high = entry.get("alert_high")
        cur_low = entry.get("alert_low")
        with col_h:
            nowy_high = st.number_input(
                "Alert gdy wynik ≥", min_value=0, max_value=100,
                value=int(cur_high) if cur_high is not None else int(default_high),
                key=f"high_{ticker}",
                help=f"Domyślnie: {default_high:.0f}",
            )
        with col_l:
            nowy_low = st.number_input(
                "Alert gdy wynik ≤", min_value=0, max_value=100,
                value=int(cur_low) if cur_low is not None else int(default_low),
                key=f"low_{ticker}",
                help=f"Domyślnie: {default_low:.0f}",
            )
        with col_save:
            st.write("")
            if st.button("💾 Zapisz progi", key=f"save_{ticker}"):
                db.set_watchlist_alerts(ticker, float(nowy_high), float(nowy_low), user_id)
                st.success("Zapisano.")

        cur_crossover = bool(entry.get("alert_crossover"))
        nowy_crossover = st.checkbox(
            "⭐ Alert o przecięciu MA50/MA200 (złoty krzyż / krzyż śmierci)",
            value=cur_crossover,
            key=f"cross_{ticker}",
            help="Powiadom, gdy średnia 50-dniowa przetnie 200-dniową - "
                 "klasyczny sygnał zmiany długoterminowego trendu.",
        )
        if nowy_crossover != cur_crossover:
            db.set_crossover_alert(ticker, nowy_crossover, user_id)

    db.update_watchlist_score(ticker, nowy_score, user_id)
    st.divider()

st.caption(
    "💡 Zmiana wyniku (np. **+5.2**) pokazuje różnicę względem "
    "ostatniej wizyty na tej stronie - nie względem wczoraj. "
    "Aby śledzić zmiany dzień po dniu i otrzymywać powiadomienia "
    "automatycznie, skonfiguruj `scheduler.py` (patrz zakładka "
    "'Ustawienia')."
)



footer()
