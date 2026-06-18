"""
Porównanie wielu spółek
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from common import (
    apply_theme,
    footer,
    kolor_dla_score,
    pobierz_analize,
    pobierz_dane,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
from tickers import PRZYKLADOWE_SPOLKI

user_id = sidebar_user()
sidebar_legenda()

with st.sidebar:
    st.divider()
    st.markdown("**Wybierz spółki do porównania**")
    domyslne = list(PRZYKLADOWE_SPOLKI.keys())[:5]
    wybrane_nazwy = st.multiselect(
        "Spółki z listy",
        list(PRZYKLADOWE_SPOLKI.keys()),
        default=domyslne,
    )
    dodatkowe = st.text_input(
        "Dodatkowe symbole oddzielone przecinkiem (opcjonalnie)",
        value="",
        placeholder="np. NFLX, ASML",
    )
    tickery = [PRZYKLADOWE_SPOLKI[n] for n in wybrane_nazwy]
    if dodatkowe.strip():
        tickery += [t.strip().upper() for t in dodatkowe.split(",") if t.strip()]

st.title("🔀 Porównanie spółek")

if not tickery:
    st.info("Wybierz przynajmniej jedną spółkę w panelu po lewej.")
    st.stop()

wyniki, bledy = [], []
with st.spinner("Pobieranie danych..."):
    for t in tickery:
        try:
            res = pobierz_analize(t)
            if "error" in res:
                bledy.append(t)
            else:
                wyniki.append(res)
        except Exception:
            bledy.append(t)

if bledy:
    st.warning(f"Nie udało się pobrać danych dla: {', '.join(bledy)}")

if not wyniki:
    st.error("Brak poprawnych danych do porównania.")
    st.stop()

tabela = pd.DataFrame([
    {
        "Spółka": r["ticker"],
        "Nazwa": r["name"],
        "Sektor": r.get("sector", "Nieznany"),
        "Cena": r["price"],
        "Waluta": r["currency"],
        "Wynik ogólny": r["total_score"],
        "Ocena": interpret_score(r["total_score"]),
    }
    for r in wyniki
]).sort_values("Wynik ogólny", ascending=False).reset_index(drop=True)

tabela.index = tabela.index + 1
tabela.index.name = "Ranking"

st.markdown(
    "Spółki posortowane od najwyższego do najniższego wyniku. "
    "**Wysoki wynik nie oznacza 'kup'** - to tylko podsumowanie "
    "sygnałów technicznych i fundamentalnych opisanych poniżej."
)

st.dataframe(
    tabela.style.background_gradient(
        subset=["Wynik ogólny"], cmap="RdYlGn", vmin=0, vmax=100
    ),
    use_container_width=True,
)

fig = go.Figure(go.Bar(
    x=tabela["Spółka"], y=tabela["Wynik ogólny"],
    marker_color=[kolor_dla_score(v) for v in tabela["Wynik ogólny"]],
    text=[f"{v:.0f}" for v in tabela["Wynik ogólny"]],
    textposition="outside",
))
fig.add_hline(y=50, line_dash="dash", line_color="#888")
fig.update_layout(
    title="Wynik ogólny - porównanie",
    height=350,
    margin=dict(l=10, r=10, t=40, b=10),
    yaxis_range=[0, 100],
    yaxis_title="Wynik (0-100)",
)
st.plotly_chart(apply_theme(fig), use_container_width=True)

csv = tabela.to_csv(index=True).encode("utf-8")
st.download_button(
    "⬇️ Pobierz wyniki jako CSV",
    data=csv,
    file_name="porownanie_spolek.csv",
    mime="text/csv",
)

st.divider()
st.markdown("#### 📈 Porównanie zachowania cen (znormalizowane)")
st.markdown(
    "Każda linia startuje od **100%** na początku okresu - dzięki temu "
    "można porównać, która spółka zyskała/straciła więcej w tym samym "
    "czasie, niezależnie od tego, ile faktycznie kosztuje jedna akcja."
)

okres_norm = st.select_slider(
    "Okres porównania",
    options=["3mo", "6mo", "1y", "2y", "5y"],
    value="1y",
    format_func=lambda x: {
        "3mo": "3 miesiące", "6mo": "6 miesięcy", "1y": "1 rok",
        "2y": "2 lata", "5y": "5 lat",
    }[x],
    key="cmp_norm_period",
)

fig_norm = go.Figure()
norm_errors = []
for r in wyniki:
    t = r["ticker"]
    try:
        df_t, _ = pobierz_dane(t, period=okres_norm)
    except Exception:
        df_t = None
    if df_t is None or df_t.empty:
        norm_errors.append(t)
        continue
    normalized = df_t["Close"] / df_t["Close"].iloc[0] * 100
    fig_norm.add_trace(go.Scatter(
        x=df_t.index, y=normalized, name=t, mode="lines",
    ))

if norm_errors:
    st.caption(f"Brak danych historycznych dla: {', '.join(norm_errors)}")

fig_norm.add_hline(y=100, line_dash="dash", line_color="#888")
fig_norm.update_layout(
    title="Zmiana ceny względem początku okresu (start = 100%)",
    height=420,
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis_title="Wartość względna (%)",
    hovermode="x unified",
)
st.plotly_chart(apply_theme(fig_norm), use_container_width=True)


# ========================================================================
# POJEDYNEK 1 vs 1 (side-by-side)
# ========================================================================
st.divider()
st.markdown("#### ⚔️ Pojedynek: spółka vs spółka")
st.markdown(
    "Wybierz dwie spółki z porównywanych powyżej, aby zobaczyć pełne "
    "rozbicie ich wyników obok siebie – wskaźnik po wskaźniku."
)

if len(wyniki) < 2:
    st.info("Dodaj przynajmniej dwie spółki, aby skorzystać z pojedynku.")
else:
    dostepne = {r["ticker"]: r for r in wyniki}
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        wybor_a = st.selectbox("Spółka A", list(dostepne.keys()), index=0, key="duel_a")
    with col_sel2:
        idx_b = 1 if len(dostepne) > 1 else 0
        wybor_b = st.selectbox("Spółka B", list(dostepne.keys()), index=idx_b, key="duel_b")

    if wybor_a == wybor_b:
        st.warning("Wybierz dwie różne spółki.")
    else:
        res_a = dostepne[wybor_a]
        res_b = dostepne[wybor_b]

        # Nagłówki z wynikiem ogólnym
        h1, h2 = st.columns(2)
        for col, res in ((h1, res_a), (h2, res_b)):
            with col:
                st.markdown(f"### {res['ticker']}")
                st.caption(res["name"])
                st.metric(
                    "Wynik ogólny", f"{res['total_score']:.0f}/100",
                    delta=interpret_score(res["total_score"]), delta_color="off",
                )
                st.caption(f"💵 {res['price']} {res['currency']} · 🏷 {res.get('sector', 'Nieznany')}")

        st.divider()

        # Rozbicie wskaźnik po wskaźniku
        st.markdown("**Rozbicie wskaźników** (zielony = wyższy wynik w danym wierszu)")
        wspolne = [k for k in res_a["components"] if k in res_b["components"]]

        from common import OPISY_WSKAZNIKOW, emoji_dla_score

        for key in wspolne:
            val_a = res_a["components"][key][0]
            val_b = res_b["components"][key][0]
            nazwa = OPISY_WSKAZNIKOW.get(key, {}).get("nazwa", key)

            c_label, c_a, c_b = st.columns([2, 1, 1])
            with c_label:
                st.markdown(f"**{nazwa}**")
            # podświetl wyższy wynik
            a_better = val_a > val_b
            b_better = val_b > val_a
            with c_a:
                strzalka = " 🟢" if a_better else ""
                st.markdown(f"{emoji_dla_score(val_a)} {val_a:.0f}{strzalka}")
            with c_b:
                strzalka = " 🟢" if b_better else ""
                st.markdown(f"{emoji_dla_score(val_b)} {val_b:.0f}{strzalka}")

        # Liczba "wygranych" wskaźników
        wins_a = sum(1 for k in wspolne if res_a["components"][k][0] > res_b["components"][k][0])
        wins_b = sum(1 for k in wspolne if res_b["components"][k][0] > res_a["components"][k][0])
        st.divider()
        st.markdown(
            f"**Podsumowanie:** {res_a['ticker']} wygrywa w **{wins_a}** wskaźnikach, "
            f"{res_b['ticker']} w **{wins_b}**. "
            f"(Pozostałe remisowe.) To nie jest rekomendacja – tylko "
            f"porównanie sygnałów."
        )


footer()
