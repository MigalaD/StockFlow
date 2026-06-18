"""
Skaner rynku
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from common import (
    apply_theme,
    footer,
    kolor_dla_score,
    sidebar_legenda,
    sidebar_user,
)
from scanner import scan_market
from tickers import (
    SKANER_EUROPA,
    SKANER_GPW,
    SKANER_KRYPTO,
    SKANER_USA,
    SKANER_WSZYSTKIE,
)
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("🔍 Skaner rynku")
st.markdown(
    "Skaner przelicza wynik dla większej grupy spółek na raz i "
    "pokazuje, które wypadają najlepiej, a które najgorzej "
    "*w danym momencie*. Przydatne do szybkiego przeglądu rynku "
    "bez ręcznego sprawdzania każdej spółki."
)

col1, col2 = st.columns([2, 1])
with col1:
    zakres = st.radio(
        "Co skanować?",
        [
            f"USA ({len(SKANER_USA)} spółek)",
            f"GPW ({len(SKANER_GPW)} spółek)",
            f"Europa Zach. ({len(SKANER_EUROPA)} spółek)",
            f"₿ Krypto ({len(SKANER_KRYPTO)} tokenów)",
            f"Wszystko ({len(SKANER_WSZYSTKIE)} spółek)",
        ],
        horizontal=True,
    )
with col2:
    st.write("")
    st.write("")
    uruchom = st.button("▶️ Uruchom skan teraz", use_container_width=True, type="primary")

last_scan = db.get_last_scan_time()
if last_scan:
    st.caption(f"Ostatni skan: {last_scan[:19].replace('T', ' ')}")
else:
    st.caption("Skan nie był jeszcze uruchamiany.")

st.warning(
    "⏱️ Skanowanie wielu spółek trwa od kilkudziesięciu sekund do "
    "kilku minut (zależnie od liczby spółek i szybkości połączenia "
    "z Yahoo Finance). Wynik jest zapisywany lokalnie, więc nie "
    "trzeba uruchamiać skanu przy każdej wizycie."
)

if uruchom:
    if zakres.startswith("USA"):
        lista = SKANER_USA
    elif zakres.startswith("GPW"):
        lista = SKANER_GPW
    elif zakres.startswith("Europa"):
        lista = SKANER_EUROPA
    elif zakres.startswith("₿"):
        lista = SKANER_KRYPTO
    else:
        lista = SKANER_WSZYSTKIE

    from scanner import scan_market

    progress_bar = st.progress(0, text="Rozpoczynanie (skanowanie równoległe)…")
    import threading
    _lock = threading.Lock()

    def progress_cb(done, total, ticker):
        progress_bar.progress(done / total, text=f"Analiza {ticker} ({done}/{total})")

    with st.spinner("Skanowanie..."):
        scan_market(lista, progress_callback=progress_cb)

    progress_bar.empty()
    st.success("Skan zakończony!")
    st.rerun()

results = db.get_scan_results()

if not results:
    st.info("Brak wyników - uruchom skan powyżej.")
    st.stop()

df_results = pd.DataFrame(results)
df_results = df_results.rename(columns={
    "ticker": "Spółka", "name": "Nazwa", "sector": "Sektor",
    "price": "Cena", "score": "Wynik",
})[["Spółka", "Nazwa", "Sektor", "Cena", "Wynik"]]

col_top, col_bottom = st.columns(2)

with col_top:
    st.markdown("#### 🟢 Top 10 - najwyższy wynik")
    top10 = df_results.head(10).reset_index(drop=True)
    top10.index = top10.index + 1
    st.dataframe(
        top10.style.background_gradient(subset=["Wynik"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
    )

with col_bottom:
    st.markdown("#### 🔴 Bottom 10 - najniższy wynik")
    bottom10 = df_results.tail(10).sort_values("Wynik").reset_index(drop=True)
    bottom10.index = bottom10.index + 1
    st.dataframe(
        bottom10.style.background_gradient(subset=["Wynik"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
    )

st.markdown("#### Pełna lista wyników")
st.dataframe(
    df_results.style.background_gradient(subset=["Wynik"], cmap="RdYlGn", vmin=0, vmax=100),
    use_container_width=True,
)

csv = df_results.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Pobierz pełne wyniki jako CSV",
    data=csv,
    file_name="skan_rynku.csv",
    mime="text/csv",
)

st.caption(
    "⚠️ Wysoki wynik w skanerze **nie oznacza 'kup'**, a niski "
    "**nie oznacza 'sprzedaj'**. To punkt wyjścia do dalszej analizy "
    "konkretnej spółki w zakładce 'Analiza jednej spółki'."
)

# ── Siła sektorów ────────────────────────────────────────────────────
from analytics import sector_strength

sektory = sector_strength(results)
if sektory:
    st.divider()
    st.markdown("#### 🏭 Siła sektorów")
    st.markdown(
        "Średni wynik spółek w każdym sektorze ze skanu – pokazuje, które "
        "branże są obecnie technicznie/fundamentalnie najmocniejsze, a które "
        "najsłabsze."
    )

    df_sekt = pd.DataFrame(sektory).rename(columns={
        "sector": "Sektor", "avg_score": "Średni wynik",
        "count": "Liczba spółek", "min_score": "Min", "max_score": "Max",
    })

    fig_sekt = go.Figure(go.Bar(
        x=df_sekt["Średni wynik"],
        y=df_sekt["Sektor"],
        orientation="h",
        marker_color=[kolor_dla_score(v) for v in df_sekt["Średni wynik"]],
        text=[f"{v:.0f}" for v in df_sekt["Średni wynik"]],
        textposition="outside",
        customdata=df_sekt["Liczba spółek"],
        hovertemplate="%{y}: %{x:.0f}/100 (%{customdata} spółek)<extra></extra>",
    ))
    fig_sekt.add_vline(x=50, line_dash="dash", line_color="#888")
    fig_sekt.update_layout(
        height=max(300, 36 * len(df_sekt)),
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_range=[0, 110], xaxis_title="Średni wynik (0–100)",
        yaxis=dict(autorange="reversed"),  # najmocniejszy na górze
    )
    st.plotly_chart(apply_theme(fig_sekt), use_container_width=True)

    st.dataframe(
        df_sekt.style.background_gradient(subset=["Średni wynik"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True, hide_index=True,
    )


footer()
