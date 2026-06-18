"""
Backtest strategii
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from common import (
    apply_theme,
    footer,
    sidebar_legenda,
    sidebar_user,
)
from backtest import backtest_score_strategy, run_threshold_grid, walk_forward_analysis
from tickers import PRZYKLADOWE_SPOLKI

user_id = sidebar_user()
sidebar_legenda()

st.title("🧪 Backtest")

st.markdown(
    "Backtest sprawdza, **co by było, gdyby** kupować spółkę, gdy "
    "uproszczony sygnał techniczny przekroczy próg 'kupna', i "
    "sprzedawać, gdy spadnie poniżej progu 'sprzedaży' - w "
    "porównaniu do prostego 'kup i trzymaj'."
)

st.error(
    "⚠️ **To narzędzie edukacyjne, nie strategia do realnego handlu.** "
    "Backtest nie uwzględnia prowizji, podatków, spreadu i poślizgu "
    "cenowego. Dobry wynik na danych historycznych **nie gwarantuje** "
    "dobrego wyniku w przyszłości - rynki się zmieniają, a reguła "
    "może być przypadkowo 'dopasowana' do przeszłości "
    "(tzw. overfitting)."
)

with st.form("backtest_form"):
    col1, col2 = st.columns([2, 1])
    with col1:
        wybrana_nazwa = st.selectbox(
            "Spółka", list(PRZYKLADOWE_SPOLKI.keys()),
            help="Możesz też wpisać własny symbol poniżej.",
        )
        wlasny_ticker = st.text_input(
            "...albo wpisz własny symbol (zastąpi wybór powyżej)",
            value="",
        )
    with col2:
        okres_bt = st.selectbox(
            "Okres testu",
            ["1y", "2y", "5y"],
            index=1,
            format_func=lambda x: {"1y": "1 rok", "2y": "2 lata", "5y": "5 lat"}[x],
        )
        kapital = st.number_input("Kapitał startowy", value=10000, step=1000, min_value=100)

    col3, col4 = st.columns(2)
    with col3:
        buy_threshold = st.slider(
            "Próg kupna (score ≥)", min_value=50, max_value=90, value=65,
            help="Gdy uproszczony score wzrośnie do tego poziomu lub wyżej, "
                 "strategia 'kupuje' (jeśli nie ma jeszcze pozycji).",
        )
    with col4:
        sell_threshold = st.slider(
            "Próg sprzedaży (score ≤)", min_value=10, max_value=50, value=35,
            help="Gdy uproszczony score spadnie do tego poziomu lub niżej, "
                 "strategia 'sprzedaje' (jeśli ma pozycję).",
        )

    uruchom_bt = st.form_submit_button("▶️ Uruchom backtest", type="primary")

if uruchom_bt:
    ticker_bt = (wlasny_ticker.strip().upper() if wlasny_ticker.strip()
                  else PRZYKLADOWE_SPOLKI[wybrana_nazwa])

    if buy_threshold <= sell_threshold:
        st.error("Próg kupna musi być wyższy niż próg sprzedaży.")
        st.stop()

    # zapisz parametry w sesji, żeby heatmapa/walk-forward mogły
    # ich użyć po kolejnym kliknięciu (bez ponownego wypełniania formularza)
    st.session_state["bt_params"] = {
        "ticker": ticker_bt, "period": okres_bt, "capital": kapital,
        "buy": buy_threshold, "sell": sell_threshold,
    }
    # nowy backtest - wyczyść stare wyniki heatmapy/walk-forward (innego tickera)
    st.session_state.pop("bt_grid", None)
    st.session_state.pop("bt_walkforward", None)

bt_params = st.session_state.get("bt_params")

if bt_params:
    ticker_bt = bt_params["ticker"]
    okres_bt = bt_params["period"]
    kapital = bt_params["capital"]
    buy_threshold = bt_params["buy"]
    sell_threshold = bt_params["sell"]

    with st.spinner(f"Liczenie backtestu dla {ticker_bt}..."):
        wynik_bt = backtest_score_strategy(
            ticker_bt, period=okres_bt,
            buy_threshold=buy_threshold, sell_threshold=sell_threshold,
            initial_capital=kapital,
        )

    if "error" in wynik_bt:
        st.error(wynik_bt["error"])
        st.stop()

    metrics = wynik_bt["metrics"]
    equity = wynik_bt["equity_curve"]
    trades = wynik_bt["trades"]

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric(
            "Strategia 'score'",
            f"{metrics['total_return']:+.1f}%",
            help=f"Wartość końcowa: {metrics['final_value']:,.0f}",
        )
    with col_b:
        st.metric(
            "Kup i trzymaj",
            f"{metrics['buyhold_return']:+.1f}%",
            help=f"Wartość końcowa: {metrics['buyhold_final_value']:,.0f}",
        )
    with col_c:
        st.metric("Liczba transakcji", metrics["num_trades"])
    with col_d:
        st.metric(
            "Skuteczność transakcji",
            f"{metrics['win_rate']:.0f}%",
            help="Procent transakcji zamkniętych z zyskiem (przed kosztami).",
        )

    col_e, col_f, col_g = st.columns(3)
    with col_e:
        st.metric(
            "Max obsunięcie kapitału",
            f"{metrics['max_drawdown']:.1f}%",
            help="Największy spadek wartości portfela od poprzedniego "
                 "szczytu - obrazuje 'najgorszy moment' tej strategii.",
        )
    with col_f:
        st.metric(
            "Sharpe ratio", f"{metrics['sharpe']:.2f}",
            help="Stosunek zwrotu do całkowitej zmienności (zannualizowany). "
                 "Wyżej = lepszy zwrot przy danym poziomie 'huśtania' "
                 "wartości portfela. Orientacyjnie: >1 dobre, >2 bardzo dobre, "
                 "<0 strategia traciła.",
        )
    with col_g:
        st.metric(
            "Sortino ratio", f"{metrics['sortino']:.2f}",
            help="Podobny do Sharpe, ale liczy tylko 'złą' zmienność "
                 "(spadki) - nie karze za gwałtowne wzrosty. Wyższy "
                 "Sortino niż Sharpe oznacza, że większość wahań "
                 "to były wzrosty.",
        )

    roznica = metrics["total_return"] - metrics["buyhold_return"]
    if roznica > 0:
        st.success(
            f"W tym okresie strategia 'score' wypadła **lepiej** niż "
            f"'kup i trzymaj' o {roznica:.1f} pkt. proc."
        )
    else:
        st.info(
            f"W tym okresie strategia 'score' wypadła **gorzej (lub tak "
            f"samo)** niż 'kup i trzymaj', różnica: {roznica:.1f} pkt. proc."
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity["Date"], y=equity["Strategy"], name="Strategia 'score'",
        line=dict(color="#2563eb", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=equity["Date"], y=equity["BuyHold"], name="Kup i trzymaj",
        line=dict(color="#888", width=2, dash="dot"),
    ))
    fig.update_layout(
        title=f"Wartość portfela: strategia vs kup i trzymaj ({ticker_bt})",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis_title="Wartość portfela",
        hovermode="x unified",
    )
    st.plotly_chart(apply_theme(fig), use_container_width=True)

    st.markdown("#### Historia transakcji")
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df.index = trades_df.index + 1
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("W tym okresie strategia nie wygenerowała żadnej transakcji.")

    if metrics["still_open"]:
        st.caption(
            "ℹ️ Ostatnia pozycja była wciąż otwarta na koniec okresu - "
            "jej wynik jest 'na papierze', nie zrealizowany."
        )

    # ----------------------------------------------------------
    # HEATMAPA PROGÓW
    # ----------------------------------------------------------
    st.divider()
    st.markdown("#### 🗺️ Heatmapa progów kupna/sprzedaży")
    st.caption(
        "Sprawdza wiele kombinacji progów kupna/sprzedaży naraz na tych "
        "samych danych - pomaga ocenić, czy wybrane progi (65/35) były "
        "dobrym wyborem, czy przypadkiem. Kolor = zwrot strategii (%) "
        "w tym okresie."
    )
    if st.button("🗺️ Policz heatmapę progów", key="run_heatmap"):
        with st.spinner("Liczenie wielu kombinacji progów..."):
            grid_result = run_threshold_grid(ticker_bt, period=okres_bt, initial_capital=kapital)
        st.session_state["bt_grid"] = grid_result

    grid_result = st.session_state.get("bt_grid")
    if grid_result and "error" not in grid_result:
        grid = grid_result["grid"]
        best = grid_result["best"]
        buyhold = grid_result["buyhold_return"]

        heat = go.Figure(data=go.Heatmap(
            z=grid.values, x=[f"{c}" for c in grid.columns], y=[f"{r}" for r in grid.index],
            colorscale="RdYlGn", zmid=buyhold,
            colorbar=dict(title="Zwrot %"),
            text=grid.values, texttemplate="%{text:.0f}",
        ))
        heat.update_layout(
            title=f"Zwrot strategii (%) dla różnych progów - 'kup i trzymaj' = {buyhold:.1f}%",
            xaxis_title="Próg kupna (score ≥)",
            yaxis_title="Próg sprzedaży (score ≤)",
            height=400,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(apply_theme(heat), use_container_width=True)
        st.caption(
            f"Najlepsza kombinacja w tym okresie: kupno≥{best['buy']}, "
            f"sprzedaż≤{best['sell']} -> {best['return']:+.1f}% "
            f"(vs kup i trzymaj: {buyhold:+.1f}%). "
            "Pamiętaj: 'najlepsza' kombinacja z przeszłości nie musi "
            "być najlepsza w przyszłości - to ilustracja overfittingu."
        )
    elif grid_result and "error" in grid_result:
        st.error(grid_result["error"])

    # ----------------------------------------------------------
    # WALK-FORWARD
    # ----------------------------------------------------------
    st.divider()
    st.markdown("#### 🚶 Test stabilności w czasie (walk-forward)")
    st.caption(
        "Dzieli historię na kilka okresów i sprawdza regułę w każdym "
        "z nich od nowa. Jeśli strategia wygrywa z 'kup i trzymaj' "
        "tylko w jednym okresie, to słaby znak - sugeruje, że "
        "działała przez przypadek w konkretnych warunkach rynkowych."
    )
    if st.button("🚶 Policz walk-forward (5 lat, 4 okna)", key="run_walkforward"):
        with st.spinner("Liczenie testu stabilności..."):
            wf_result = walk_forward_analysis(
                ticker_bt, period="5y", buy_threshold=buy_threshold,
                sell_threshold=sell_threshold, n_windows=4, initial_capital=kapital,
            )
        st.session_state["bt_walkforward"] = wf_result

    wf_result = st.session_state.get("bt_walkforward")
    if wf_result and "error" not in wf_result:
        windows = wf_result["windows"]
        summary = wf_result["summary"]

        wf_df = pd.DataFrame(windows).rename(columns={
            "okres_od": "Od", "okres_do": "Do",
            "strategia_%": "Strategia %", "kup_i_trzymaj_%": "Kup i trzymaj %",
            "lepsza_niz_bh": "Lepsza niż B&H?",
            "liczba_transakcji": "Transakcje", "max_obsuniecie_%": "Max obsunięcie %",
        })
        wf_df.index = wf_df.index + 1
        st.dataframe(wf_df, use_container_width=True)

        st.markdown(
            f"**Strategia była lepsza niż 'kup i trzymaj' w "
            f"{summary['wins']} z {summary['n_windows']} okresów "
            f"({summary['win_rate_pct']:.0f}%).**"
        )
        if summary["win_rate_pct"] < 50:
            st.warning(
                "Strategia wygrała w mniej niż połowie okresów - to "
                "sygnał, że może nie być stabilna/wiarygodna."
            )
    elif wf_result and "error" in wf_result:
        st.error(wf_result["error"])



footer()
