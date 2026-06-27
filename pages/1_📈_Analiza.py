# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Analiza jednej spółki
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from common import (
    section_header, empty_state,
    LEGENDA_SCORE, KOLOR_NEUTRALNY, KOLOR_DOBRY, KOLOR_AKCENTU, KOLOR_TEKST,
    OPISY_WSKAZNIKOW,
    apply_theme,
    banner_dane_niedostepne,
    emoji_dla_score, kolor_dla_score,
    footer,
    pobierz_analize,
    pobierz_dane,
    pobierz_dane_live,
    pobierz_dane_binance,
    pobierz_dane_intraday,
    INTRADAY_INTERVALS,
    INTRADAY_MAX_HISTORIA,
    policz_historie_score,
    rysuj_wykres_ceny,
    rysuj_wykres_historii_score,
    rysuj_wykres_rsi,
    rysuj_wykres_scoru,
    score_banner,
    interpret_score,
    sidebar_legenda,
    sidebar_user,
    ticker_search_widget,
    dodaj_do_ostatnio_ogladanych,
    pokaz_ostatnio_ogladane,
)
from stock_analyzer import WEIGHTS, interpret_score
from intraday_signals import (
    atr_summary,
    stochastic_summary,
    compute_stochastic,
    compute_obv,
    detect_obv_divergence,
    detect_support_resistance,
)
from pdf_report import generate_stock_report
from strategies import STRATEGIE, evaluate_strategy, interpret_match
from tickers import PRZYKLADOWE_SPOLKI
import forecasting
import database as db
import external_data

user_id = sidebar_user()
sidebar_legenda()

st.title("📈 Analiza spółki")

with st.sidebar:
    st.divider()
    tryb = st.radio(
        "Sposób wyboru",
        ["Z listy przykładowych", "Wyszukaj", "Wpisz symbol"],
        label_visibility="collapsed",
    )

    if tryb == "Z listy przykładowych":
        wybrana_nazwa = st.selectbox("Spółka", list(PRZYKLADOWE_SPOLKI.keys()))
        ticker = PRZYKLADOWE_SPOLKI[wybrana_nazwa]
    elif tryb == "Wyszukaj":
        ticker = ticker_search_widget(
            label="Szukaj po nazwie lub symbolu",
            key="analiza_search",
        )
        # K: keyboard shortcut hint
        st.caption("💡 Wpisz i wciśnij **Enter** aby wyszukać")
    else:
        ticker = st.text_input(
            "Symbol spółki (np. AAPL, CDR.WA)", value="AAPL",
            help="Symbole z GPW mają sufiks .WA, np. CDR.WA dla CD Projekt",
        ).strip().upper()

    # J: Ostatnio przeglądane
    recent_click = pokaz_ostatnio_ogladane(key_prefix="analiza_recent")
    if recent_click:
        ticker = recent_click

    okres = st.select_slider(
        "Zakres historii na wykresie",
        options=["3mo", "6mo", "1y", "2y", "5y"],
        value="1y",
        format_func=lambda x: {
            "3mo": "3 miesiące", "6mo": "6 miesięcy", "1y": "1 rok",
            "2y": "2 lata", "5y": "5 lat",
        }[x],
    )

if not ticker:
    st.info("Wpisz symbol spółki w panelu po lewej.")
    st.stop()

with st.spinner(f"Analizuję {ticker}…"):
    # Score i metadane (Yahoo) – niezależne od źródła wykresu.
    try:
        wynik = pobierz_analize(ticker)
    except Exception:
        wynik = {"error": "fetch_failed"}

    # J: Zapisz do ostatnio przeglądanych
    if "error" not in wynik:
        dodaj_do_ostatnio_ogladanych(ticker)

    # Dane wykresu: Binance dla krypto (live), Yahoo jako fallback/default.
    # Rozdzielone celowo – awaria jednego źródła nie blokuje drugiego.
    df, info, _zrodlo_wykresu = None, {}, "Yahoo Finance (~15 min opóźnienia)"
    _fetch_errors = []

    # Próba 1: Binance (dla krypto)
    if external_data.is_binance_supported(ticker):
        try:
            df_binance, _ = pobierz_dane_binance(ticker, okres=okres)
            if df_binance is not None and not df_binance.empty:
                df = df_binance
                _zrodlo_wykresu = "Binance (na żywo)"
        except Exception as e:
            _fetch_errors.append(f"Binance: {e}")

    # Próba 2: Yahoo Finance (zawsze, jako fallback lub główne źródło)
    if df is None:
        try:
            df_yf, info_yf = pobierz_dane(ticker, period=okres)
            if df_yf is not None and not df_yf.empty:
                df = df_yf
                info = info_yf or {}
        except Exception as e:
            _fetch_errors.append(f"Yahoo: {e}")

    # Próba 3: Dla krypto – yfinance bezpośrednio z krótkim cache (bypass rate-limiter)
    if df is None and external_data.is_binance_supported(ticker):
        try:
            import yfinance as _yf
            _stock = _yf.Ticker(ticker)
            _df3 = _stock.history(period=okres, interval="1d")
            if _df3 is not None and not _df3.empty:
                from stock_analyzer import rsi as _rsi, macd as _macd, bollinger_bands as _bb, compute_vwap as _vwap
                _df3["RSI"]   = _rsi(_df3["Close"])
                _df3["MA20"]  = _df3["Close"].rolling(20).mean()
                _df3["MA50"]  = _df3["Close"].rolling(50).mean()
                _df3["MA200"] = _df3["Close"].rolling(200).mean()
                _df3["MACD"], _df3["MACD_signal"] = _macd(_df3["Close"])
                _df3["BB_mid"], _df3["BB_upper"], _df3["BB_lower"] = _bb(_df3["Close"])
                _df3["VWAP"] = _vwap(_df3)
                df = _df3
                _zrodlo_wykresu = "Yahoo Finance (bezpośredni)"
        except Exception as e:
            _fetch_errors.append(f"Yahoo direct: {e}")

    # Gdy Binance dostarczył wykres ale Yahoo score failuje – zachowaj df.
    # Gdy obydwa failują – df=None i wynik zawiera error, st.stop() poniżej.

# Rozróżniamy: awaria Yahoo Finance vs nieprawidłowy symbol.
# Brak danych wykresu I brak score → totalny fail, pokaż banner.
if df is None and wynik.get("error") == "fetch_failed":
    banner_dane_niedostepne()
    st.stop()

# Brak wykresu – nieprawidłowy symbol lub oba źródła niedostępne.
if df is None:
    if external_data.is_binance_supported(ticker):
        # Krypto obsługiwane przez Binance – oba źródła failują → problem sieciowy
        banner_dane_niedostepne()
        st.caption(
            f"Symbol **{ticker}** jest rozpoznany (kryptowaluta). "
            "Dane chwilowo niedostępne – zarówno Binance jak i Yahoo Finance "
            "nie odpowiadają. Spróbuj ponownie za chwilę."
        )
    else:
        st.error(
            f"Nie udało się znaleźć danych dla symbolu **{ticker}**. "
            "Sprawdź, czy symbol jest prawidłowy (np. AAPL dla Apple, "
            "CDR.WA dla CD Projekt na GPW, BTC-USD dla Bitcoina)."
        )
    st.stop()

# Brak score (Yahoo failuje) ale mamy wykres z Binance – ostrzeż i kontynuuj.
if "error" in wynik:
    st.warning(
        "⚠️ Wynik (score) chwilowo niedostępny – Yahoo Finance ma przejściowy "
        "problem. Wykres pochodzi z Binance i działa normalnie. "
        "Odśwież stronę za chwilę, aby załadować pełną analizę."
    )
    # Wypełnij wynik minimalnymi danymi, żeby strona się nie wysypała.
    wynik = {
        "total_score": None,
        "name": ticker,
        "currency": "USD",
        "price": df["Close"].iloc[-1] if df is not None and not df.empty else None,
        "sector": "—",
        "industry": "—",
        "asset_type": "crypto" if external_data.is_binance_supported(ticker) else "other",
        "components": {},
        "weights": {},
        "vwap": None,
        "calendar_info": {},
        "news": [],
    }

nazwa_firmy = (
    info.get("longName")          # yfinance info dict
    or info.get("name")           # wynik dict z analyze_ticker
    or ticker
)
waluta = info.get("currency") or wynik.get("currency", "USD")
cena = wynik.get("price")
score = wynik.get("total_score")
score_st = wynik.get("score_st")          # score krótkoterminowy (swing)
sektor = wynik.get("sector", "Nieznany")
branza = wynik.get("industry", "Nieznana")
asset_type = wynik.get("asset_type", "stock")
asset_label = wynik.get("asset_type_label", "Akcja")

# G: Sticky header — zawsze widoczny przy scrollowaniu
st.markdown(
    "<div style='position:sticky;top:0;z-index:999;"
    "background:linear-gradient(180deg,#1F2937 85%,rgba(31,41,55,0) 100%);"
    "padding:8px 0 4px 0;margin-bottom:4px;'>"
    "<span style='font-family:Inter,sans-serif;font-weight:700;font-size:1.05rem;'>"
    + ticker +
    "</span>"
    "<span style='font-family:Inter;font-size:0.82rem;opacity:0.5;margin-left:8px;'>"
    + (nazwa_firmy[:35] + "…" if len(nazwa_firmy) > 35 else nazwa_firmy) +
    "</span>"
    "</div>",
    unsafe_allow_html=True,
)

col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
with col1:
    st.subheader(f"{nazwa_firmy} ({ticker})")
    if asset_type == "stock" and sektor and sektor != "Nieznany":
        st.caption(f"🏷️ Sektor: **{sektor}** • Branża: {branza}")
    elif asset_type in ("etf", "etf_commodity"):
        kategoria = wynik.get("category") or "Nieznana"
        dostawca = wynik.get("fund_family") or "Nieznany"
        ikona = "🛢️" if asset_type == "etf_commodity" else "📊"
        st.caption(f"{ikona} {asset_label} • Kategoria: **{kategoria}** • Dostawca: {dostawca}")
    elif asset_type == "commodity":
        st.caption("🛢️ Surowiec / kontrakt - brak danych fundamentalnych spółki")
    else:
        st.caption(f"🏷️ {asset_label}")
with col2:
    cena_str = f"{cena} {waluta}" if cena is not None else "—"
    st.metric(
        "Aktualna cena", cena_str,
        help="Ostatnia dostępna cena zamknięcia.",
    )
with col3:
    if score is not None:
        st.metric(
            "📈 Wynik DT", f"{score:.0f} / 100",
            delta=interpret_score(score), delta_color="off",
            help="Wynik długoterminowy: trend, fundamenty, wycena, dywidenda, momentum 21d/63d.",
        )
    else:
        st.metric("📈 Wynik DT", "—", help="Score niedostępny – Yahoo Finance chwilowo nieosiągalny.")
with col4:
    if score_st is not None:
        st.metric(
            "⚡ Wynik ST", f"{score_st:.0f} / 100",
            delta=interpret_score(score_st), delta_color="off",
            help="Wynik krótkoterminowy (swing): RSI-7, Stochastik, momentum 5d/10d, OBV, VWAP, Bollinger %B.",
        )
    else:
        st.metric("⚡ Wynik ST", "—", help="Score krótkoterminowy niedostępny.")
with col5:
    st.write("")
    st.write("")
    if st.button("⭐ Dodaj do watchlist", use_container_width=True):
        db.add_to_watchlist(ticker, user_id)
        db.update_watchlist_score(ticker, score, user_id)
        st.success(f"{ticker} dodano do watchlist ({user_id})!")

# ── D: Kontekst aktualnego instrumentu w sidebarze ───────────────────
with st.sidebar:
    st.divider()
    kolor_s = kolor_dla_score(score) if score is not None else KOLOR_NEUTRALNY
    score_str = f"{score:.0f}/100" if score is not None else "—"
    st.markdown(
        "<div style='font-family:Inter,sans-serif;padding:4px 0;'>"
        "<div style='font-size:0.72rem;opacity:0.5;text-transform:uppercase;"
        "letter-spacing:0.06em;margin-bottom:4px;'>Analizujesz</div>"
        "<div style='font-weight:700;font-size:1rem;'>" + ticker + "</div>"
        "<div style='font-size:0.82rem;opacity:0.65;margin-bottom:6px;'>"
        + (nazwa_firmy[:28] + "…" if len(nazwa_firmy) > 28 else nazwa_firmy) +
        "</div>"
        "<div style='display:flex;gap:8px;'>"
        "<span style='background:" + kolor_s + "18;color:" + kolor_s + ";"
        "padding:2px 8px;border-radius:999px;font-size:0.78rem;font-weight:600;"
        "border:1px solid " + kolor_s + "40;'>DT " + score_str + "</span>"
        + (
            "<span style='background:" + kolor_dla_score(score_st) + "18;color:"
            + kolor_dla_score(score_st) + ";padding:2px 8px;border-radius:999px;"
            "font-size:0.78rem;font-weight:600;border:1px solid "
            + kolor_dla_score(score_st) + "40;'>ST " + str(round(score_st)) + "/100</span>"
            if score_st is not None else ""
        ) +
        "</div></div>",
        unsafe_allow_html=True,
    )

with st.expander("📓 Szybki wpis do dziennika dla tej spółki"):
    DECYZJE_QUICK = ["Kupno", "Sprzedaż", "Obserwacja", "Zwiększenie pozycji",
                     "Zmniejszenie pozycji", "Bez zmian (HOLD)", "Inne"]
    with st.form(f"quick_journal_{ticker}", clear_on_submit=True):
        col_qa, col_qb = st.columns([1, 2])
        with col_qa:
            quick_decyzja = st.selectbox("Decyzja", DECYZJE_QUICK, key=f"qd_{ticker}")
        with col_qb:
            quick_powod = st.text_input("Powód (opcjonalnie)", key=f"qr_{ticker}")
        quick_submit = st.form_submit_button("➕ Zapisz wpis")
    if quick_submit:
        from datetime import date as _date
        db.add_journal_entry(
            user_id, _date.today().isoformat(), ticker, quick_decyzja,
            quick_powod.strip(), score or 0, cena or 0,
        )
        st.success(f"Dodano wpis do dziennika dla {ticker} (wynik {score:.0f}/100, cena {cena}).")


# Dodatkowy kontekst: porównanie sektorowe i beta vs indeks
info_bits = []
sector_cmp = wynik.get("sector_pe_comparison")
if sector_cmp:
    info_bits.append(f"📐 {sector_cmp}")

beta_info = wynik.get("beta_info")
if beta_info:
    beta = beta_info["beta"]
    corr = beta_info["correlation"]
    idx_name = "WIG20" if beta_info["index"] == "^WIG20" else "S&P 500"
    if beta > 1.2:
        beta_opis = f"rusza się SILNIEJ niż {idx_name} (większe wahania)"
    elif beta < 0.8:
        beta_opis = f"rusza się SŁABIEJ niż {idx_name} (mniejsze wahania)"
    else:
        beta_opis = f"rusza się PODOBNIE jak {idx_name}"
    info_bits.append(
        f"📊 Beta={beta:.2f}, korelacja={corr:.2f} z {idx_name} - {beta_opis}"
    )

rel = wynik.get("relative_strength")
if rel:
    idx_name = "WIG20" if rel["index"] == "^WIG20" else "S&P 500"
    out = rel["outperformance_pct"]
    if out > 0:
        rel_opis = f"**lepiej** niż {idx_name} o {out:+.1f} pkt proc."
    else:
        rel_opis = f"**gorzej** niż {idx_name} o {out:.1f} pkt proc."
    info_bits.append(
        f"💪 Siła relatywna (1 rok): spółka {rel['stock_return_pct']:+.1f}%, "
        f"{idx_name} {rel['index_return_pct']:+.1f}% → radzi sobie {rel_opis}"
    )

crossover = wynik.get("ma_crossover")
if crossover:
    if crossover.get("crossed") and crossover["type"] == "golden":
        info_bits.append("⭐ **Złoty krzyż** dzisiaj - MA50 przecięła MA200 od dołu (klasyczny sygnał byczy)")
    elif crossover.get("crossed") and crossover["type"] == "death":
        info_bits.append("💀 **Krzyż śmierci** dzisiaj - MA50 spadła poniżej MA200 (klasyczny sygnał niedźwiedzi)")
    elif crossover["state"] == "golden":
        info_bits.append("📈 Trend długoterminowy: MA50 powyżej MA200 (układ byczy)")
    else:
        info_bits.append("📉 Trend długoterminowy: MA50 poniżej MA200 (układ niedźwiedzi)")

score_banner(score if score is not None else 50, len(wynik.get("components", {})))

if info_bits:
    with st.expander("ℹ️ Kontekst rynkowy (beta, siła relatywna, crossover)", expanded=False):
        for bit in info_bits:
            st.markdown(bit)
        st.caption(
            "Informacje orientacyjne — nie wchodzą do wyniku score, "
            "ale pomagają ocenić kontekst makro i branżowy."
        )

red_flags = wynik.get("red_flags") or []
if red_flags:
    with st.expander(f"🚩 Na co zwrócić uwagę ({len(red_flags)})", expanded=False):
        for flag in red_flags:
            st.markdown(f"- {flag}")
        st.caption(
            "To sygnały do dalszego sprawdzenia, nie automatyczne "
            "'nie kupuj'. Część z nich może mieć dobre wyjaśnienie "
            "(np. dług na ekspansję) - sprawdź raporty finansowe spółki."
        )

tab1, tab_intraday, tab_analiza, tab_forecast, tab_strategie, tab_pdf = st.tabs([
    "📈 Wykres",
    "⚡ Sygnały ST",
    "📊 Analiza szczegółowa",
    "🔮 Scenariusze",
    "🎯 Strategie",
    "📄 PDF",
])
# Aliasy dla wstecznej zgodności (tab_news, tab2, tab3, tab4, tab5, tab6
# są teraz sekcjami wewnątrz tab_analiza)
tab_news = None  # obsługiwane w tab_analiza
tab2 = None      # obsługiwane w tab_analiza
tab3 = None      # obsługiwane w tab_analiza
tab4 = None      # obsługiwane w tab_analiza
tab5 = None      # obsługiwane w tab_analiza
tab6 = None      # obsługiwane w tab_analiza

with tab1:
    # ── Selektor interwału ────────────────────────────────────────────
    intv_options = list(INTRADAY_INTERVALS.keys())
    intv_labels  = [INTRADAY_INTERVALS[k]["label"] for k in intv_options]

    intv_col, ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2.2, 1.4, 1, 1.2, 1])
    with intv_col:
        wybrany_intv = st.select_slider(
            "Interwał wykresu",
            options=intv_options,
            value="1d",
            format_func=lambda k: INTRADAY_INTERVALS[k]["label"],
            key="chart_interval",
        )
    with ctrl1:
        # Dla interwałów intraday świece są bardziej czytelne – ustaw jako domyślne
        domyslny_tryb = "Świece" if wybrany_intv != "1d" else "Linia"
        tryb_wykresu = st.radio(
            "Typ wykresu", ["Linia", "Świece"],
            index=["Linia", "Świece"].index(domyslny_tryb),
            horizontal=True, key="chart_type",
        )
    with ctrl2:
        pokaz_ma20 = st.checkbox("MA 20", value=(wybrany_intv == "1d"), key="show_ma20")
    with ctrl3:
        pokaz_bb = st.checkbox("Wstęgi Bollingera", value=False, key="show_bb")
    with ctrl4:
        pokaz_vwap = st.checkbox("VWAP", value=False, key="show_vwap")

    # Komunikat o dostępnej historii i opóźnieniu
    max_hist = INTRADAY_MAX_HISTORIA.get(wybrany_intv, "")
    if wybrany_intv == "1d":
        st.caption(f"📅 Interwał dzienny · historia: {max_hist} · 📡 {_zrodlo_wykresu}")
    elif external_data.is_binance_supported(ticker):
        st.caption(
            f"📅 Interwał {INTRADAY_INTERVALS[wybrany_intv]['label']} · "
            f"historia: ~{max_hist} · 📡 **Binance (na żywo, brak opóźnienia)**"
        )
    else:
        st.caption(
            f"📅 Interwał {INTRADAY_INTERVALS[wybrany_intv]['label']} · "
            f"historia dostępna: ~{max_hist} · "
            f"📡 Yahoo Finance (~15 min opóźnienia)"
        )

    # ── Tryb na żywo ──────────────────────────────────────────────────
    live1, live2 = st.columns([1.3, 2.7])
    with live1:
        tryb_live = st.toggle(
            "🔴 Tryb na żywo", value=False, key="live_mode",
            help=(
                "Wykres odświeża się automatycznie. "
                "Krypto (Binance): prawdziwy real-time. "
                "Akcje/ETF (Yahoo): nowy punkt co ~15 min."
            ),
        )
    with live2:
        if tryb_live:
            interwal_live = st.select_slider(
                "Częstotliwość odświeżania",
                options=[15, 30, 60, 120, 300],
                value=60,
                format_func=lambda s: f"co {s} s" if s < 60 else f"co {s // 60} min",
                key="live_interval",
            )
        else:
            interwal_live = None

    def _rysuj_panel_wykresu(auto: bool):
        """Rysuje wykres ceny + RSI + VWAP.

        auto=True: pobiera świeższe dane przez pobierz_dane_intraday (krótki TTL).
        Routing: Binance dla krypto (live), Yahoo dla pozostałych.
        """
        if auto:
            df_fresh, zrodlo_fresh = pobierz_dane_intraday(ticker, interval=wybrany_intv)
            df_chart = df_fresh if df_fresh is not None else df
            zrodlo_fresh = zrodlo_fresh or _zrodlo_wykresu

            # Alpaca live quote dla akcji USA (bid/ask)
            if external_data.is_alpaca_configured() and external_data.is_alpaca_supported(ticker):
                alpaca_quote = external_data.get_alpaca_quote(ticker)
                if alpaca_quote:
                    st.caption(
                        f"🟢 **Alpaca (na żywo):** {alpaca_quote['price']:.2f} {waluta} "
                        f"(bid {alpaca_quote['bid']:.2f} / ask {alpaca_quote['ask']:.2f})"
                    )
            st.caption(
                f"🔄 Ostatnia aktualizacja: {datetime.now():%H:%M:%S} · "
                f"📡 {zrodlo_fresh}"
            )
        else:
            # Statyczny tryb: dla interwału 1d używamy df już pobranego,
            # dla intraday pobieramy przez pobierz_dane_intraday.
            if wybrany_intv == "1d":
                df_chart = df
            else:
                df_fresh, _ = pobierz_dane_intraday(ticker, interval=wybrany_intv)
                df_chart = df_fresh if df_fresh is not None else df

        st.plotly_chart(
            rysuj_wykres_ceny(
                df_chart, nazwa_firmy, tryb=tryb_wykresu,
                pokaz_ma20=pokaz_ma20, pokaz_bollinger=pokaz_bb,
                pokaz_vwap=pokaz_vwap,
            ),
            use_container_width=True,
        )
        # źródło widoczne w caption interwału powyżej

        st.plotly_chart(rysuj_wykres_rsi(df_chart), use_container_width=True)

        # VWAP summary (zawsze na podstawie df dziennego dla spójności ze score)
        vwap_info = wynik.get("vwap")
        if vwap_info:
            if vwap_info["above"]:
                st.success(
                    f"📈 Cena ({vwap_info['price']}) jest **powyżej VWAP** "
                    f"({vwap_info['vwap']}) o {vwap_info['distance_pct']:+.1f}% – "
                    f"kupujący płacą więcej niż średnia ważona obrotem (siła popytu)."
                )
            else:
                st.info(
                    f"📉 Cena ({vwap_info['price']}) jest **poniżej VWAP** "
                    f"({vwap_info['vwap']}) o {vwap_info['distance_pct']:+.1f}% – "
                    f"cena niżej niż średnia ważona obrotem (słabszy popyt)."
                )

    if tryb_live:
        @st.fragment(run_every=interwal_live)
        def _wykres_na_zywo():
            _rysuj_panel_wykresu(auto=True)
        _wykres_na_zywo()
        st.caption("🔴 Tryb na żywo aktywny. Wyłącz przełącznik, aby zatrzymać.")
    else:
        _rysuj_panel_wykresu(auto=False)

    opisy_wykresu = []
    if wybrany_intv == "1d":
        opisy_wykresu.append(
            "**Średnie kroczące** (MA 20/50/200) wygładzają cenę i pokazują trend "
            "w różnych horyzontach: 20 dni = krótki, 200 dni = długi."
        )
    else:
        opisy_wykresu.append(
            f"**Interwał {INTRADAY_INTERVALS[wybrany_intv]['label']}** – każda świeca/punkt "
            f"to jeden przedział czasowy. MA i wstęgi liczone na świecach intraday "
            f"(mają sens dopiero przy >20 świecach historii)."
        )
    if pokaz_bb:
        opisy_wykresu.append(
            "**Wstęgi Bollingera** to średnia 20 świec ± 2 odchylenia standardowe."
        )
    if pokaz_vwap:
        opisy_wykresu.append(
            "**VWAP** (Volume Weighted Average Price) – średnia cena ważona wolumenem."
        )
    if tryb_wykresu == "Świece":
        opisy_wykresu.append("**Świece:** zielona = wzrost, czerwona = spadek w danym przedziale.")
    st.caption("  \n".join(opisy_wykresu))

with tab_analiza:
    # ── Sekcja A: Newsy i wydarzenia ─────────────────────────────────
    section_header("Newsy i wydarzenia", "📰")
    section_header("Najbliższe wydarzenia", "📅")
    cal = wynik.get("calendar_info") or {}
    earnings_date = cal.get("earnings_date")
    ex_div_date = cal.get("ex_dividend_date")
    
    if not earnings_date and not ex_div_date:
        st.caption("Brak danych o najbliższych wydarzeniach dla tej spółki.")
    else:
        col_e, col_d = st.columns(2)
        with col_e:
            if earnings_date:
                st.metric("📊 Najbliższe wyniki finansowe", earnings_date)
                st.caption(
                    "Wokół tej daty cena często wykazuje większą "
                    "zmienność niż zwykle - publikacja wyników bywa "
                    "niespodzianką (pozytywną lub negatywną)."
                )
            else:
                st.caption("Brak danych o dacie najbliższych wyników.")
        with col_d:
            if ex_div_date:
                st.metric("💰 Dywidenda (ex-dividend)", ex_div_date)
                st.caption(
                    "Data 'ex-dividend' to dzień, od którego kupujący "
                    "akcję nie ma już prawa do najbliższej dywidendy."
                )
            else:
                st.caption("Spółka nie wypłaca dywidendy / brak danych.")
    
    st.divider()
    section_header("Ostatnie newsy", "📰")
    news_list = wynik.get("news_list") or []
    if not news_list:
        st.caption("Brak dostępnych newsów dla tej spółki.")
    else:
        st.caption(
            "Lista ostatnich nagłówków z Yahoo Finance - to one wpływają "
            "na wskaźnik 'Sentyment newsów' w zakładce 'Szczegóły wyniku'."
        )
        for item in news_list:
            title = item["title"]
            if item.get("link"):
                st.markdown(f"**[{title}]({item['link']})**")
            else:
                st.markdown(f"**{title}**")
            meta_bits = [b for b in [item.get("publisher"), item.get("published")] if b]
            if meta_bits:
                st.caption(" • ".join(meta_bits))

    st.divider()
    # ── Sekcja B: Szczegóły wyniku ────────────────────────────────────
    section_header("Szczegóły wyniku DT", "🧮",
                   "Jak każdy wskaźnik wpłynął na końcowy wynik długoterminowy")
    st.plotly_chart(rysuj_wykres_scoru(wynik["components"]), use_container_width=True)
    
    wagi = wynik.get("weights", WEIGHTS)
    
    if wynik.get("asset_type") != "stock":
        st.caption(
            f"ℹ️ To **{wynik.get('asset_type_label', 'inny instrument')}** - "
            f"wskaźniki niedostępne dla tego typu aktywa (np. P/E, "
            f"dywidenda, fundamenty spółki) zostały wyłączone, a wagi "
            f"pozostałych {len(wynik['components'])} wskaźników "
            f"przeliczone tak, by sumowały się do 100%."
        )
    
    section_header("Co dokładnie sprawdziliśmy?")
    for key, (val, note) in wynik["components"].items():
        opis = OPISY_WSKAZNIKOW.get(key, {
            "nazwa": key,
            "opis": "Brak opisu dla tego wskaźnika.",
        })
        waga = wagi[key]
        with st.expander(f"{emoji_dla_score(val)} {opis['nazwa']} — wynik: {val:.0f}/100 (waga: {waga:.0%})"):
            st.write(opis["opis"])
            st.caption(f"Szczegóły techniczne: {note}")
    
    eksport_df = pd.DataFrame([
        {
            "Wskaźnik": OPISY_WSKAZNIKOW[k]["nazwa"],
            "Wynik": v,
            "Waga": wagi[k],
            "Szczegóły": note,
        }
        for k, (v, note) in wynik["components"].items()
    ])
    csv = eksport_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Pobierz szczegóły wyniku jako CSV",
        data=csv,
        file_name=f"analiza_{ticker}.csv",
        mime="text/csv",
    )

    st.divider()
    # ── Sekcja C: Historia sygnału ────────────────────────────────────
    section_header("Historia sygnału", "🕒")
    st.markdown(
        "Poniższy wykres pokazuje, jak zmieniał się **uproszczony sygnał "
        "techniczny** (na podstawie RSI, trendu i MACD) w ostatnich "
        "dniach. Pomaga zobaczyć, czy sytuacja spółki się poprawia "
        "czy pogarsza.",
        help="Ten wykres NIE zawiera wyceny, dywidendy i sentymentu, "
             "bo te nie mają pełnej historii dziennej. Pokazuje tylko "
             "część techniczną score.",
    )
    hist_df = policz_historie_score(df, dni=90)
    if len(hist_df) < 2:
        st.info("Niewystarczająca ilość danych historycznych do narysowania wykresu.")
    else:
        st.plotly_chart(rysuj_wykres_historii_score(hist_df), use_container_width=True)
        zmiana = hist_df["Score"].iloc[-1] - hist_df["Score"].iloc[0]
        if zmiana > 3:
            kierunek = "poprawił się 📈"
        elif zmiana < -3:
            kierunek = "pogorszył się 📉"
        else:
            kierunek = "pozostał stabilny ➡️"
        st.caption(
            f"W ciągu ostatnich {len(hist_df)} dni handlowych sygnał "
            f"techniczny **{kierunek}** (zmiana o {zmiana:+.1f} punktu)."
        )

with tab_strategie:
    # ── Sekcja A: Strategie inwestycyjne ─────────────────────────────
    section_header("Dopasowanie do stylów inwestowania", "🎯")
    st.markdown(
        "Wybierz styl inwestowania, który Cię interesuje. Dashboard "
        "sprawdzi, **ile warunków tej strategii spełnia obecnie ta "
        "spółka** - to pomaga ocenić, czy dana spółka pasuje do "
        "Twojego podejścia."
    )
    
    if wynik.get("asset_type") != "stock":
        st.warning(
            f"⚠️ To **{wynik.get('asset_type_label', 'inny instrument')}** - "
            "checklisty strategii zawierają warunki dotyczące dywidendy, "
            "P/E i fundamentów spółki, które dla tego typu instrumentu "
            "nie mają danych (będą wyświetlane jako niespełnione). "
            "Najwięcej sensu mają tu warunki techniczne (trend, RSI, MACD, momentum)."
        )
    
    strategia_key = st.selectbox(
        "Strategia",
        list(STRATEGIE.keys()),
        format_func=lambda k: f"{STRATEGIE[k]['ikona']} {STRATEGIE[k]['nazwa']}",
        help="Każda strategia ma inną checklistę warunków - ta sama "
             "spółka może 'pasować' do jednej i nie pasować do innej.",
    )
    
    ocena_strategii = evaluate_strategy(strategia_key, df, info, wynik["components"])
    st.info(ocena_strategii["opis"])
    
    match_pct = ocena_strategii["match_pct"]
    match_kolor = kolor_dla_score(match_pct)
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.metric(
            "Zgodność ze strategią",
            f"{ocena_strategii['met']} / {ocena_strategii['total']}",
            delta=f"{match_pct:.0f}%", delta_color="off",
        )
    with col_b:
        st.markdown(
            f"""
            <div style="
                background-color: {match_kolor}22;
                border-left: 6px solid {match_kolor};
                padding: 14px 18px;
                border-radius: 6px;
                margin-top: 8px;
            ">
                <b>{interpret_match(match_pct)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    section_header("Lista warunków")
    for opis_warunku, spelniony, szczegoly in ocena_strategii["conditions"]:
        ikona = "✅" if spelniony else "❌"
        st.markdown(f"{ikona} **{opis_warunku}**")
        st.caption(f"   {szczegoly}")
    
    st.caption(
        "Pamiętaj: spełnienie wszystkich warunków checklisty **nie jest "
        "gwarancją sukcesu** - to tylko ustrukturyzowany sposób patrzenia "
        "na dane, zgodny z wybranym stylem inwestowania."
    )

    st.divider()
    # ── Sekcja B: Słowniczek wskaźników ──────────────────────────────
    section_header("Co to znaczy?", "📚",
                   "Proste wyjaśnienie każdego wskaźnika używanego w analizie")
    st.markdown(
        """
        ### Jak działa ten dashboard?
    
        Dla każdej spółki sprawdzamy **10 różnych sygnałów** - część
        opisuje zachowanie ceny w przeszłości, część opisuje, jak
        "tania" lub "droga" jest spółka względem jej zysków, część
        dotyczy dywidendy i głębszych fundamentów (wzrost, dług,
        cash flow), a jeden dotyczy ostatnich newsów.
    
        Każdy sygnał otrzymuje punktację od 0 do 100, gdzie:
        - **100** = sygnał wyraźnie pozytywny
        - **50** = brak wyraźnego sygnału
        - **0** = sygnał wyraźnie negatywny
    
        Wszystkie sygnały są łączone w jeden **wynik ogólny**, gdzie
        niektóre mają większe znaczenie (większą "wagę") niż inne.
    
        ### Strategie inwestycyjne
    
        Zakładka "Strategie inwestycyjne" sprawdza, czy spółka spełnia
        typowe kryteria danego stylu inwestowania (trend following,
        kupowanie spadków, inwestowanie w wartość, momentum). Różne
        strategie mogą dawać różne wnioski dla tej samej spółki -
        to normalne, bo każda szuka czegoś innego.
    
        ### Watchlist, portfolio, skaner i backtest
    
        - **Watchlist** - zapisuje obserwowane spółki w lokalnej bazie
          danych, żeby śledzić zmiany wyniku w czasie.
        - **Portfolio** - wpisz swoje rzeczywiste pozycje i sprawdź
          zysk/stratę, dywersyfikację i średni wynik portfela.
        - **Skaner rynku** - przelicza wynik dla wielu spółek na raz
          i pokazuje ranking Top/Bottom.
        - **Backtest** - sprawdza, jak wypadłaby prosta reguła
          "kupuj gdy score > X, sprzedawaj gdy score < Y" na
          danych historycznych, w porównaniu do "kup i trzymaj",
          wraz z metrykami ryzyka (Sharpe, Sortino) i testem
          stabilności w czasie (walk-forward).
    
        ### Scenariusze cenowe ("Prognoza")
    
        Zakładka "Scenariusze cenowe" **nie przewiduje** ceny - pokazuje
        zakres możliwych wyników (metoda Monte Carlo / GBM) na podstawie
        historycznej zmienności, plus dwie proste ekstrapolacje trendu
        (regresja liniowa, wygładzanie Holta). Zakres szybko się
        rozszerza w czasie - to normalne i pokazuje rzeczywistą
        niepewność, nie błąd modelu.
    
        ### Najważniejsze ograniczenia
    
        - To narzędzie patrzy **tylko w przeszłość**.
        - Wysoki wynik **nie gwarantuje** wzrostu ceny, a niski
          wynik **nie gwarantuje** spadku.
        - Narzędzie nie zna Twojej sytuacji finansowej, celów ani
          tolerancji na ryzyko.
    
        **To narzędzie ma pomóc Ci zrozumieć dane, a nie podejmować
        decyzje za Ciebie.** Przed jakąkolwiek inwestycją warto
        zasięgnąć porady licencjonowanego doradcy finansowego.
        """
    )

with tab_pdf:
    st.markdown(
        "Wygeneruj raport PDF z pełną analizą tej spółki: wynik ogólny, "
        "wykres ceny, rozbicie na wszystkie wskaźniki, dodatkowy "
        "kontekst (sektor/beta), ostrzeżenia i (opcjonalnie) wybraną "
        "strategię inwestycyjną. Przydatne do zapisania 'stanu na dziś' "
        "albo wysłania komuś."
    )
    
    strategia_pdf_key = st.selectbox(
        "Dołącz strategię inwestycyjną do raportu (opcjonalnie)",
        ["(bez strategii)"] + list(STRATEGIE.keys()),
        format_func=lambda k: k if k == "(bez strategii)"
        else f"{STRATEGIE[k]['ikona']} {STRATEGIE[k]['nazwa']}",
        key="pdf_strategy_select",
    )
    
    if st.button("📄 Wygeneruj raport PDF", type="primary"):
        with st.spinner("Generowanie raportu PDF..."):
            strategy_result = None
            if strategia_pdf_key != "(bez strategii)":
                strategy_result = evaluate_strategy(strategia_pdf_key, df, info, wynik["components"])
    
            try:
                import tempfile
                out_path = tempfile.NamedTemporaryFile(
                    suffix=f"_{ticker}.pdf", delete=False
                ).name
                generate_stock_report(wynik, df, out_path, strategy_result)
                with open(out_path, "rb") as f:
                    pdf_bytes = f.read()
                st.session_state["pdf_bytes"] = pdf_bytes
                st.session_state["pdf_name"] = f"raport_{ticker}.pdf"
                st.success("Raport wygenerowany!")
            except Exception as e:
                st.error(f"Nie udało się wygenerować raportu: {e}")
                st.caption(
                    "Sprawdź, czy zainstalowane są pakiety: "
                    "`pip install reportlab matplotlib`"
                )
    
    if st.session_state.get("pdf_bytes") and st.session_state.get("pdf_name", "").endswith(f"{ticker}.pdf"):
        st.download_button(
            "⬇️ Pobierz raport PDF",
            data=st.session_state["pdf_bytes"],
            file_name=st.session_state["pdf_name"],
            mime="application/pdf",
        )


footer()
