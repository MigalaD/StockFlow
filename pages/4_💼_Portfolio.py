"""
Portfolio
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from common import (
    LEGENDA_SCORE,
    apply_theme,
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
import portfolio as portfolio_mod
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("💼 Portfolio")
st.markdown(
    "Wpisz swoje rzeczywiste pozycje (ile akcji, po jakiej cenie "
    "kupione), żeby zobaczyć aktualną wartość, zysk/stratę, "
    "dywersyfikację sektorową i średni wynik portfela. "
    "**To narzędzie analityczne - nie zarządza prawdziwymi środkami "
    "i niczego nie kupuje/sprzedaje za Ciebie.**"
)

with st.form("dodaj_pozycje", clear_on_submit=True):
    col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
    with col_a:
        poz_ticker = st.text_input(
            "Symbol", placeholder="np. AAPL, CDR.WA",
        )
    with col_b:
        poz_shares = st.number_input(
            "Liczba akcji", min_value=0.0, value=1.0, step=1.0,
        )
    with col_c:
        poz_price = st.number_input(
            "Cena zakupu (za 1 akcję)", min_value=0.0, value=0.0, step=0.01,
        )
    with col_d:
        poz_date = st.date_input("Data zakupu")

    poz_notes = st.text_input("Notatka (opcjonalnie)", placeholder="np. długoterminowo")
    dodaj_poz = st.form_submit_button("➕ Dodaj pozycję", type="primary")

if dodaj_poz:
    if not poz_ticker.strip() or poz_shares <= 0 or poz_price <= 0:
        st.error("Wypełnij symbol, liczbę akcji (>0) i cenę zakupu (>0).")
    else:
        db.add_position(
            user_id, poz_ticker.strip().upper(), poz_shares, poz_price,
            poz_date.isoformat(), poz_notes.strip(),
        )
        st.success(f"Dodano pozycję {poz_ticker.strip().upper()} do portfela.")

st.divider()

with st.spinner("Liczenie wartości portfela..."):
    analiza_portfela = portfolio_mod.analyze_portfolio(user_id, pobierz_analize)

if not analiza_portfela["positions"] and not analiza_portfela["errors"]:
    st.info(
        "Portfolio jest puste. Dodaj pierwszą pozycję powyżej, "
        "np. AAPL, 5 akcji po 180 USD."
    )
    st.stop()

if analiza_portfela["errors"]:
    st.warning(
        "Nie udało się pobrać danych dla: "
        + ", ".join(analiza_portfela["errors"])
    )

totals = analiza_portfela["totals"]
if totals:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Wartość portfela", f"{totals['total_value']:,.2f}")
    with col2:
        st.metric(
            "Zysk / strata",
            f"{totals['total_pnl']:+,.2f}",
            delta=f"{totals['total_pnl_pct']:+.1f}%",
        )
    with col3:
        st.metric("Koszt zakupu (suma)", f"{totals['total_cost']:,.2f}")
    with col4:
        st.metric(
            "Średni wynik portfela", f"{totals['weighted_score']:.0f}/100",
            delta=interpret_score(totals["weighted_score"]), delta_color="off",
            help=LEGENDA_SCORE + "\n\nŚredni wynik ważony aktualną "
                 "wartością każdej pozycji (większe pozycje mają "
                 "większy wpływ).",
        )

    st.caption(
        "ℹ️ Wartości w mieszanych walutach są tu po prostu zsumowane "
        "bez przeliczania kursów - jeśli masz pozycje w różnych "
        "walutach, traktuj sumę orientacyjnie."
    )

for warn in analiza_portfela["warnings"]:
    st.warning(warn)

st.markdown("#### Pozycje")
for p in analiza_portfela["positions"]:
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
    with col1:
        st.markdown(f"**{p['name']}** ({p['ticker']})")
        st.caption(f"🏷️ {p['sector']} • {p['shares']:g} akcji od {p['buy_date']}")
        if p["notes"]:
            st.caption(f"📝 {p['notes']}")
    with col2:
        st.metric("Cena zakupu", f"{p['buy_price']:.2f} {p['currency']}")
    with col3:
        st.metric("Cena aktualna", f"{p['current_price']:.2f} {p['currency']}")
    with col4:
        st.metric("Wartość", f"{p['current_value']:,.2f}")
    with col5:
        st.metric("P&L", f"{p['pnl']:+,.2f}", delta=f"{p['pnl_pct']:+.1f}%")
    with col6:
        st.metric(
            "Wynik", f"{p['score']:.0f}/100",
            delta=interpret_score(p["score"]), delta_color="off",
            help=LEGENDA_SCORE,
        )
        if st.button("🗑️ Usuń", key=f"del_pos_{p['id']}"):
            db.remove_position(p["id"], user_id)
            st.rerun()
    st.divider()

if analiza_portfela["allocation_by_sector"]:
    st.markdown("#### Alokacja sektorowa")
    alloc = analiza_portfela["allocation_by_sector"]
    fig = go.Figure(go.Pie(
        labels=list(alloc.keys()), values=list(alloc.values()),
        hole=0.4,
    ))
    fig.update_layout(
        height=350, margin=dict(l=10, r=10, t=20, b=10),
        showlegend=True,
    )
    st.plotly_chart(apply_theme(fig), use_container_width=True)
    st.caption(
        "Im bardziej portfel jest 'pokrojony' na wiele sektorów, "
        "tym mniej zależy od losu jednej branży. To nie jest porada "
        "dotycząca optymalnej alokacji - to tylko opis obecnej "
        "struktury."
    )

csv_df = pd.DataFrame(analiza_portfela["positions"])
if not csv_df.empty:
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        csv = csv_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Pobierz portfolio jako CSV",
            data=csv, file_name="portfolio.csv", mime="text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        from excel_export import build_workbook, suggested_filename
        # Dołącz też dziennik i historię score do skoroszytu
        journal_rows = db.get_journal_entries(user_id)
        score_hist = {}
        for p in analiza_portfela["positions"]:
            hist = db.get_score_history(p["ticker"])
            if hist:
                score_hist[p["ticker"]] = hist
        xlsx_bytes = build_workbook(
            portfolio_rows=analiza_portfela["positions"],
            journal_rows=journal_rows,
            score_history=score_hist,
        )
        st.download_button(
            "⬇️ Pobierz pełny raport (Excel)",
            data=xlsx_bytes,
            file_name=suggested_filename("portfolio"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Skoroszyt .xlsx z zakładkami: Portfolio, Dziennik, Historia score "
                 "(z kolorowaniem zysków/strat).",
        )

# --- Korelacja między pozycjami ---
tickery_portfolio = list({p["ticker"] for p in analiza_portfela["positions"]})
if len(tickery_portfolio) >= 2:
    st.divider()
    st.markdown("#### 🔗 Korelacja między pozycjami")
    st.markdown(
        "Pokazuje, jak bardzo ceny Twoich pozycji ruszają się razem "
        "(na podstawie dziennych zmian cen z ostatnich 6 miesięcy). "
        "**Wysoka korelacja (bliska 1.0)** oznacza, że dwie pozycje "
        "zachowują się podobnie - nawet jeśli są z różnych sektorów, "
        "mogą NIE dywersyfikować portfela tak, jak mogłoby się wydawać. "
        "**Korelacja bliska 0 lub ujemna** oznacza, że pozycje "
        "zachowują się niezależnie (lub odwrotnie) - to wzmacnia "
        "dywersyfikację."
    )

    with st.spinner("Liczenie korelacji..."):
        corr_result = portfolio_mod.compute_correlation_matrix(tickery_portfolio, period="6mo")

    if corr_result["errors"]:
        st.caption(f"Brak danych dla: {', '.join(corr_result['errors'])}")

    matrix = corr_result["matrix"]
    if matrix is None or matrix.shape[0] < 2:
        st.info("Potrzeba przynajmniej 2 pozycji z dostępnymi danymi historycznymi.")
    else:
        heat_corr = go.Figure(data=go.Heatmap(
            z=matrix.values, x=list(matrix.columns), y=list(matrix.index),
            colorscale="RdBu_r", zmin=-1, zmax=1,
            colorbar=dict(title="Korelacja"),
            text=matrix.values, texttemplate="%{text:.2f}",
        ))
        heat_corr.update_layout(
            title="Korelacja dziennych zwrotów (ostatnie 6 miesięcy)",
            height=max(300, 80 * len(matrix)),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(apply_theme(heat_corr), use_container_width=True)

        if corr_result["high_pairs"]:
            st.warning(
                "⚠️ Wysoka korelacja (≥ 0.75) między: "
                + ", ".join(f"**{a}** i **{b}** ({c:.2f})" for a, b, c in corr_result["high_pairs"])
            )
        else:
            st.caption("Brak par z bardzo wysoką korelacją (≥ 0.75) - dobry znak dla dywersyfikacji.")



footer()
