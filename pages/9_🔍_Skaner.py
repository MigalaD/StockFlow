# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Skaner rynku – tryb długoterminowy i krótkoterminowy (swing-trading)
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

# ── Tryb skanowania ───────────────────────────────────────────────────
tryb_col, zakres_col = st.columns([1.4, 2.6])
with tryb_col:
    tryb_score = st.radio(
        "Tryb oceny",
        ["📈 Długoterminowy", "⚡ Krótkoterminowy (swing)"],
        horizontal=False,
        help=(
            "**Długoterminowy:** P/E, fundamenty, trend MA200, dywidenda, "
            "momentum 21d/63d. Pytanie: 'czy to dobra spółka na miesiące/lata?'\n\n"
            "**Krótkoterminowy (swing):** RSI-7, Stochastik, momentum 5d/10d, "
            "wolumen 3d, OBV, VWAP, Bollinger %B. Pytanie: 'czy jest sygnał "
            "do ruchu w ciągu dni/tygodni?'"
        ),
    )
    jest_st = tryb_score.startswith("⚡")

with zakres_col:
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

if jest_st:
    st.info(
        "⚡ **Tryb krótkoterminowy (swing-trading):** dane dzienne z ~15 min "
        "opóźnieniem. Wskaźniki odpowiadają na pytanie 'czy jest momentum "
        "do ruchu w ciągu kilku dni/tygodni'. Nie nadaje się do prawdziwego "
        "intraday day-tradingu (minutowe/sekundowe notowania)."
    )

uruchom = st.button("▶️ Uruchom skan teraz", use_container_width=False, type="primary")

last_scan = db.get_last_scan_time()
if last_scan:
    st.caption(f"Ostatni skan: {last_scan[:19].replace('T', ' ')}")
else:
    st.caption("Skan nie był jeszcze uruchamiany.")

st.warning(
    "⏱️ Skanowanie wielu spółek trwa od kilkudziesięciu sekund do "
    "kilku minut (zależnie od liczby spółek i szybkości połączenia "
    "z Yahoo Finance). Wynik jest zapisywany lokalnie."
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

    import threading
    progress_bar = st.progress(0, text="Rozpoczynanie (skanowanie równoległe)…")
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
    st.info("Brak wyników – uruchom skan powyżej.")
    st.stop()

# Kolumna score zależna od trybu
score_col = "score_st" if jest_st else "score"
score_label = "Wynik ST" if jest_st else "Wynik DT"
score_opis = (
    "Wynik krótkoterminowy (0–100): RSI-7, Stochastik, momentum 5d/10d, "
    "wolumen 3d, OBV, VWAP, Bollinger %B."
    if jest_st else
    "Wynik długoterminowy (0–100): trend, fundamenty, wycena, dywidenda, "
    "momentum 21d/63d, sentyment."
)

# Sprawdź czy kolumna score_st istnieje w wynikach (starszy skan może jej nie mieć)
brak_st = jest_st and any(r.get("score_st") is None for r in results[:3])
if brak_st:
    st.warning(
        "⚠️ Wyniki skanu nie zawierają ocen krótkoterminowych – "
        "uruchom nowy skan, aby je wygenerować."
    )
    score_col = "score"
    score_label = "Wynik DT (uruchom skan dla ST)"

df_results = pd.DataFrame(results)

# Buduj kolumny do wyświetlenia
kolumny_show = {
    "ticker": "Spółka",
    "name": "Nazwa",
    "sector": "Sektor",
    "price": "Cena",
}
# Zawsze pokazuj oba score obok siebie
if "score_st" in df_results.columns:
    kolumny_show["score"] = "Wynik DT"
    kolumny_show["score_st"] = "Wynik ST"
else:
    kolumny_show["score"] = "Wynik"

df_show = df_results.rename(columns=kolumny_show)[list(kolumny_show.values())]

# Sortuj po wybranym trybie
sort_col = "Wynik ST" if (jest_st and "Wynik ST" in df_show.columns) else "Wynik DT" if "Wynik DT" in df_show.columns else "Wynik"
df_show = df_show.sort_values(sort_col, ascending=False).reset_index(drop=True)

# Określ kolumny do gradientu
gradient_cols = [c for c in ["Wynik DT", "Wynik ST", "Wynik"] if c in df_show.columns]

st.divider()
st.markdown(f"#### Ranking — {'⚡ Ocena krótkoterminowa (swing)' if jest_st else '📈 Ocena długoterminowa'}")
st.caption(score_opis)

col_top, col_bottom = st.columns(2)
with col_top:
    st.markdown(f"#### 🟢 Top 10")
    top10 = df_show.head(10).reset_index(drop=True)
    top10.index = top10.index + 1
    st.dataframe(
        top10.style.background_gradient(subset=gradient_cols, cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
    )

with col_bottom:
    st.markdown(f"#### 🔴 Bottom 10")
    bottom10 = df_show.tail(10).sort_values(sort_col).reset_index(drop=True)
    bottom10.index = bottom10.index + 1
    st.dataframe(
        bottom10.style.background_gradient(subset=gradient_cols, cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
    )

st.markdown("#### Pełna lista wyników")
st.dataframe(
    df_show.style.background_gradient(subset=gradient_cols, cmap="RdYlGn", vmin=0, vmax=100),
    use_container_width=True,
    hide_index=True,
)

csv = df_show.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Pobierz pełne wyniki jako CSV",
    data=csv,
    file_name=f"skan_rynku_{'st' if jest_st else 'dt'}.csv",
    mime="text/csv",
)

st.caption(
    "⚠️ Wysoki wynik w skanerze **nie oznacza 'kup'**, a niski "
    "**nie oznacza 'sprzedaj'**. To punkt wyjścia do dalszej analizy "
    "konkretnej spółki w zakładce 'Analiza jednej spółki'."
)

# ── Siła sektorów ────────────────────────────────────────────────────
from analytics import sector_strength

# Dla trybu ST przelicz siłę sektorów na podstawie score_st
results_for_sector = []
for r in results:
    r2 = dict(r)
    if jest_st and r.get("score_st") is not None:
        r2["score"] = r["score_st"]
    results_for_sector.append(r2)

sektory = sector_strength(results_for_sector)
if sektory:
    st.divider()
    st.markdown(
        f"#### 🏭 Siła sektorów — "
        f"{'⚡ krótkoterminowa' if jest_st else '📈 długoterminowa'}"
    )
    st.markdown(
        "Średni wynik spółek w każdym sektorze ze skanu – pokazuje, które "
        "branże są obecnie najmocniejsze, a które najsłabsze."
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
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(apply_theme(fig_sekt), use_container_width=True)

    st.dataframe(
        df_sekt.style.background_gradient(
            subset=["Średni wynik"], cmap="RdYlGn", vmin=0, vmax=100
        ),
        use_container_width=True, hide_index=True,
    )

footer()
