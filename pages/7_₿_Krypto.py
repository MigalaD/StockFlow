# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Kryptowaluty
=============
Przegląd popularnych kryptowalut z oceną techniczną (score). Krypto nie ma
fundamentów spółki, więc score opiera się wyłącznie na analizie technicznej,
plus dwie składowe specyficzne dla krypto: zmienność kalibrowana pod realia
rynku krypto i siła względem Bitcoina (dominacja).

Cena bazowa pochodzi z Yahoo Finance (do liczenia score - spójność z resztą
aplikacji), ale gdy dostępny jest Binance, NADPISUJEMY wyświetlaną cenę
świeższą wartością live z Binance (sekundy, nie ~15 min jak Yahoo). To jedyne
miejsce w aplikacji z prawdziwym source'em real-time - krypto jako jedyna
klasa aktywów ma do tego darmowe, w pełni otwarte API.
"""
import streamlit as st
import pandas as pd

from common import (
    section_header, empty_state,
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
import external_data

user_id = sidebar_user()
sidebar_legenda()

st.title("₿ Kryptowaluty")
st.warning(
    "⚠️ **Kryptowaluty są wyjątkowo zmienne i ryzykowne.** Score uwzględnia "
    "analizę techniczną (trend, RSI, MACD, momentum) skalowaną pod realia "
    "rynku krypto oraz siłę względem Bitcoina – kryptowaluty nie mają "
    "fundamentów spółki (P/E, dywidendy, przychodów). "
    "Wynik **nie jest** prognozą ani rekomendacją."
)

# ── Dominacja BTC (CoinGecko) ─────────────────────────────────────────
dominance = external_data.get_btc_dominance()
if dominance:
    dcol1, dcol2, dcol3 = st.columns(3)
    with dcol1:
        st.metric("Dominacja BTC", f"{dominance['btc_dominance_pct']:.1f}%")
    with dcol2:
        st.metric("Dominacja ETH", f"{dominance['eth_dominance_pct']:.1f}%")
    with dcol3:
        st.metric(
            "Cały rynek krypto (24h)",
            f"{dominance['market_cap_change_24h_pct']:+.1f}%",
        )
    st.caption(
        "Źródło: CoinGecko. Dominacja BTC = udział Bitcoina w łącznej "
        "kapitalizacji rynku krypto – wysoka dominacja zwykle oznacza, że "
        "kapitał ucieka z altcoinów do BTC (\"bezpieczniejszej\" krypto); "
        "spadająca dominacja bywa nazywana \"altseason\"."
    )
else:
    st.caption(
        "ℹ️ Dane o dominacji BTC chwilowo niedostępne (CoinGecko) – "
        "score nadal liczony normalnie, tylko bez tego dodatkowego kontekstu."
    )

st.divider()

# ── Pobranie i analiza wszystkich pozycji z listy ────────────────────
wyniki = []
binance_uzyte = 0
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

        # Spróbuj nadpisać cenę świeższą wartością z Binance (live).
        cena_live = cena
        zrodlo_ceny = "Yahoo Finance (~15 min opóźnienia)"
        zmiana_24h = None
        live_data = external_data.get_binance_price(ticker)
        if live_data:
            cena_live = live_data["price"]
            zrodlo_ceny = "Binance (na żywo)"
            zmiana_24h = live_data["change_24h_pct"]
            binance_uzyte += 1

        wyniki.append({
            "nazwa": nazwa,
            "ticker": ticker,
            "opis": opis,
            "name": res["name"],
            "price": cena_live,
            "price_yahoo": cena,
            "currency": res["currency"],
            "score": res["total_score"],
            "zrodlo_ceny": zrodlo_ceny,
            "zmiana_24h": zmiana_24h,
        })

if not wyniki:
    st.error(
        "Nie udało się pobrać danych dla żadnej kryptowaluty. "
        "Yahoo Finance może mieć chwilowy problem – spróbuj ponownie za chwilę."
    )
    st.stop()

wyniki.sort(key=lambda w: w["score"], reverse=True)

if binance_uzyte > 0:
    st.success(
        f"🔴 {binance_uzyte}/{len(wyniki)} cen na żywo z Binance "
        f"(sekundy, nie ~15 minut jak Yahoo Finance)."
    )

# ── Tabela zbiorcza ──────────────────────────────────────────────────
df_show = pd.DataFrame([{
    "Nazwa": w["nazwa"].split(" (")[0],
    "Ticker": w["ticker"],
    "Cena (USD)": w["price"],
    "Zmiana 24h": f"{w['zmiana_24h']:+.1f}%" if w["zmiana_24h"] is not None else "—",
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
        delta_str = f"{w['zmiana_24h']:+.1f}% (24h)" if w["zmiana_24h"] is not None else None
        st.metric(
            "Cena",
            f"${w['price']:,.2f}" if w["currency"] == "USD"
            else f"{w['price']} {w['currency']}",
            delta=delta_str,
        )
        st.caption(f"📡 {w['zrodlo_ceny']}")
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
st.caption(
    "ℹ️ Score liczony jest zawsze na podstawie danych Yahoo Finance (dla "
    "spójności z resztą aplikacji) – cena z Binance jest wyświetlana "
    "dodatkowo jako świeższa wartość, ale nie zmienia wyniku score."
)

footer()
