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
    LEGENDA_SCORE,
    OPISY_WSKAZNIKOW,
    apply_theme,
    banner_dane_niedostepne,
    emoji_dla_score,
    footer,
    kolor_dla_score,
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
    sidebar_legenda,
    sidebar_user,
    ticker_search_widget,
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
    else:
        ticker = st.text_input(
            "Symbol spółki (np. AAPL, CDR.WA)", value="AAPL",
            help="Symbole z GPW mają sufiks .WA, np. CDR.WA dla CD Projekt",
        ).strip().upper()

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

if info_bits:
    with st.expander("ℹ️ Dodatkowy kontekst (sektor / rynek)", expanded=False):
        for bit in info_bits:
            st.markdown(bit)
        st.caption(
            "Te informacje są orientacyjne i NIE wchodzą do wyniku ogólnego "
            "- pomagają ocenić kontekst, ale nie zmieniają score."
        )

score_banner(score if score is not None else 50, len(wynik.get("components", {})))

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

tab1, tab_news, tab_intraday, tab2, tab3, tab_forecast, tab4, tab5, tab6 = st.tabs([
    "📈 Wykres ceny",
    "📰 Newsy i wydarzenia",
    "⚡ Sygnały krótkoterminowe",
    "🧮 Szczegóły wyniku",
    "🕒 Historia sygnału",
    "🔮 Scenariusze cenowe",
    "🎯 Strategie inwestycyjne",
    "📚 Co to znaczy?",
    "📄 Raport PDF",
])

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
        if not auto:
            st.caption(f"📡 Dane wykresu: {_zrodlo_wykresu}")

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

with tab_news:
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

with tab_intraday:
    # ── Score krótkoterminowy – prominently on top ─────────────────
    st_col1, st_col2 = st.columns([1, 3])
    with st_col1:
        if score_st is not None:
            from stock_analyzer import interpret_score as _interp
            st.metric(
                "⚡ Wynik krótkoterminowy",
                f"{score_st:.0f} / 100",
                delta=_interp(score_st), delta_color="off",
                help=(
                    "Score swing-tradingowy (0–100). Składowe: RSI-7, Stochastik %K, "
                    "momentum 5d/10d, wolumen 3d, OBV, VWAP, Bollinger %B. "
                    "Dane dzienne (~15 min opóźnienia)."
                ),
            )
        else:
            st.metric("⚡ Wynik krótkoterminowy", "—")
    with st_col2:
        st.caption(
            "Dane dzienne z Yahoo Finance (~15 min opóźnienia) – narzędzie dla "
            "**swing-tradingu** (pozycje trzymane dni/tygodnie), nie dla intraday day-tradingu."
        )
        if score is not None and score_st is not None:
            roznica = score_st - score
            if abs(roznica) >= 10:
                kierunek = "wyższy niż długoterminowy" if roznica > 0 else "niższy niż długoterminowy"
                st.caption(
                    f"💡 Wynik ST ({score_st:.0f}) jest o **{abs(roznica):.0f} pkt {kierunek}** "
                    f"({score:.0f} DT) – sygnały krótkoterminowe różnią się od długoterminowych."
                )

    st.divider()

    atr_info   = atr_summary(df)
    stoch_info = stochastic_summary(df)
    levels     = detect_support_resistance(df)
    obv_series = compute_obv(df)
    divergence = detect_obv_divergence(df)

    # ── PANEL SYNTEZY ─────────────────────────────────────────────
    # Zbiera wszystkie sygnały w jedno zdanie z oceną sytuacji.
    sygnaly_bycze    = []
    sygnaly_niedzw   = []
    sygnaly_neutralne = []

    if stoch_info:
        if stoch_info["signal"] == "wyprzedanie":
            sygnaly_bycze.append("wyprzedanie stochastyku (<20)")
        elif stoch_info["signal"] == "przegrzanie":
            sygnaly_niedzw.append("przegrzanie stochastyku (>80)")
        if stoch_info["crossed"] == "bullish":
            sygnaly_bycze.append("bullish crossover %K/%D")
        elif stoch_info["crossed"] == "bearish":
            sygnaly_niedzw.append("bearish crossover %K/%D")

    if divergence:
        if divergence["type"] == "bullish":
            sygnaly_bycze.append("bycza dywergencja OBV")
        else:
            sygnaly_niedzw.append("niedźwiedzia dywergencja OBV")

    if levels and atr_info and cena is not None:
        najblizszy_opor   = next((l for l in levels["resistance"] if l > cena), None)
        najblizsze_wsprcie = next((l for l in reversed(levels["support"]) if l < cena), None)
        if najblizszy_opor and najblizsze_wsprcie:
            dist_opor  = (najblizszy_opor - cena) / cena * 100
            dist_wsp   = (cena - najblizsze_wsprcie) / cena * 100
            if dist_wsp < dist_opor * 0.5:
                sygnaly_niedzw.append("cena blisko wsparcia")
            elif dist_opor < dist_wsp * 0.5:
                sygnaly_bycze.append("cena blisko oporu")

    n_b = len(sygnaly_bycze)
    n_n = len(sygnaly_niedzw)

    if n_b > 0 and n_n == 0:
        ikona_syntezy = "🟢"
        kolor_syntezy = "success"
        tekst_syntezy = f"**Sygnały pozytywne ({n_b}):** " + ", ".join(sygnaly_bycze)
    elif n_n > 0 and n_b == 0:
        ikona_syntezy = "🔴"
        kolor_syntezy = "error"
        tekst_syntezy = f"**Sygnały negatywne ({n_n}):** " + ", ".join(sygnaly_niedzw)
    elif n_b > 0 and n_n > 0:
        ikona_syntezy = "🟡"
        kolor_syntezy = "warning"
        tekst_syntezy = (
            f"**Mieszane sygnały** – bycze: {', '.join(sygnaly_bycze)} | "
            f"niedźwiedzie: {', '.join(sygnaly_niedzw)}"
        )
    else:
        ikona_syntezy = "⚪"
        kolor_syntezy = "info"
        tekst_syntezy = "**Brak wyraźnych sygnałów krótkoterminowych** – wskaźniki w strefie neutralnej."

    getattr(st, kolor_syntezy)(f"{ikona_syntezy} {tekst_syntezy}")
    st.caption(
        "Synteza nie jest rekomendacją – to skrót tego, co mówią poszczególne "
        "wskaźniki poniżej. Zawsze sprawdzaj każdy z nich samodzielnie."
    )

    st.divider()

    # ── ATR + KONKRETNY STOP-LOSS ──────────────────────────────────
    col_atr, col_stoch = st.columns(2)
    with col_atr:
        st.markdown("**📏 ATR – zasięg ruchu i sugerowany stop-loss**")
        if atr_info:
            st.metric(
                "Średni dzienny zasięg ruchu",
                f"{atr_info['atr']:.2f} {waluta}",
                delta=f"{atr_info['atr_pct']:.1f}% ceny",
                delta_color="off",
            )
            if cena is not None:
                stop_1x = cena - atr_info["atr"]
                stop_15 = cena - 1.5 * atr_info["atr"]
                stop_tekst = (
                    "**Sugerowany stop-loss:**\n\n"
                    f"- Ciąsny (1× ATR): **{stop_1x:.2f} {waluta}**\n\n"
                    f"- Szeroki (1.5× ATR): **{stop_15:.2f} {waluta}**"
                )
                st.markdown(stop_tekst)
            st.caption(
                "Stop-loss ciasniejszy niż ATR bywa 'wybijany' przez zwykły szum "
                "rynkowy, a nie faktyczne odwrócenie trendu."
            )
        else:
            st.caption("Brak wystarczających danych do wyliczenia ATR.")

    # ── STOCHASTIK Z WYKRESEM ──────────────────────────────────────
    with col_stoch:
        st.markdown("**🎯 Stochastik – pozycja w zakresie wahań**")
        if stoch_info:
            st.metric(
                "Aktualny stan",
                f"%K = {stoch_info['k']:.0f}  |  %D = {stoch_info['d']:.0f}",
                delta=stoch_info["signal"],
                delta_color="off",
            )
            if stoch_info["crossed"] == "bullish":
                st.success("🟢 %K przecięło %D od dołu – sygnał bullish")
            elif stoch_info["crossed"] == "bearish":
                st.error("🔴 %K przecięło %D od góry – sygnał bearish")
            else:
                st.caption("Brak przecięcia %K/%D w ostatnim dniu.")
            st.caption("< 20 = wyprzedanie  |  > 80 = przegrzanie")
        else:
            st.caption("Brak wystarczających danych.")

    # Mini wykres stochastyku za ostatnie 60 dni
    if stoch_info:
        k_series, d_series = compute_stochastic(df)
        k60 = k_series.dropna().iloc[-60:]
        d60 = d_series.dropna().iloc[-60:]
        if not k60.empty:
            fig_stoch = go.Figure()
            fig_stoch.add_trace(go.Scatter(
                x=k60.index, y=k60.values, name="%K",
                line=dict(color="#f59e0b", width=1.6),
            ))
            fig_stoch.add_trace(go.Scatter(
                x=d60.index, y=d60.values, name="%D (sygnał)",
                line=dict(color="#94a3b8", width=1.2, dash="dot"),
            ))
            fig_stoch.add_hline(y=80, line_dash="dot", line_color="#ef4444",
                                annotation_text="Przegrzanie (80)", opacity=0.5)
            fig_stoch.add_hline(y=20, line_dash="dot", line_color="#22c55e",
                                annotation_text="Wyprzedanie (20)", opacity=0.5)
            fig_stoch.update_layout(
                height=200, margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(range=[0, 100]),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(apply_theme(fig_stoch), use_container_width=True)

    st.divider()

    # ── WSPARCIE I OPÓR Z ODLEGŁOŚCIĄ % ───────────────────────────
    st.markdown("**📐 Wsparcie i opór – odległość od aktualnej ceny**")
    if levels["support"] or levels["resistance"]:
        col_sup, col_res = st.columns(2)
        with col_sup:
            st.caption("🟢 Wsparcie")
            for lvl in reversed(levels["support"]):
                if cena is not None:
                    dist = (cena - lvl) / cena * 100
                    st.markdown(
                        f"**{lvl:.2f} {waluta}** &nbsp; "
                        f"<span style='color:#94a3b8'>−{dist:.1f}% od ceny</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"`{lvl:.2f} {waluta}`")
        with col_res:
            st.caption("🔴 Opór")
            for lvl in levels["resistance"]:
                if cena is not None:
                    dist = (lvl - cena) / cena * 100
                    st.markdown(
                        f"**{lvl:.2f} {waluta}** &nbsp; "
                        f"<span style='color:#94a3b8'>+{dist:.1f}% od ceny</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"`{lvl:.2f} {waluta}`")

        # Wykres ceny z poziomami i etykietami odległości
        fig_sr = go.Figure()
        fig_sr.add_trace(go.Scatter(
            x=df.index, y=df["Close"], name="Cena",
            line=dict(color="#2563eb", width=1.6),
        ))
        for lvl in levels["support"]:
            fig_sr.add_hline(
                y=lvl, line_dash="dot", line_color="#16a34a", opacity=0.7,
                annotation_text=f"Wsp. {lvl:.0f}",
                annotation_position="left",
            )
        for lvl in levels["resistance"]:
            fig_sr.add_hline(
                y=lvl, line_dash="dot", line_color="#dc2626", opacity=0.7,
                annotation_text=f"Opór {lvl:.0f}",
                annotation_position="left",
            )
        if cena is not None:
            fig_sr.add_hline(
                y=cena, line_dash="solid", line_color="#f59e0b", opacity=0.9,
                annotation_text=f"Teraz {cena:.0f}",
                annotation_position="right",
            )
        fig_sr.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        )
        st.plotly_chart(apply_theme(fig_sr), use_container_width=True)
        st.caption(
            "Poziomy wykryte automatycznie z lokalnych ekstremów ostatnich ~120 dni. "
            "To historyczne punkty zatrzymania – rynek nie musi ich 'respektować'."
        )
    else:
        st.caption("Brak wystarczających danych do wykrycia poziomów.")

    st.divider()

    # ── OBV I DYWERGENCJA ─────────────────────────────────────────
    st.markdown("**📊 OBV – czy wolumen popiera trend?**")
    obv_valid = obv_series.dropna()
    if not obv_valid.empty:
        if divergence:
            if divergence["type"] == "bearish":
                st.error(f"🔴 Dywergencja niedźwiedzia: {divergence['description']}")
            else:
                st.success(f"🟢 Dywergencja bycza: {divergence['description']}")
        else:
            st.info("✅ Brak dywergencji – wolumen zgodny z kierunkiem ceny (ostatnie 20 dni).")

        fig_obv = go.Figure()
        fig_obv.add_trace(go.Scatter(
            x=obv_valid.index, y=obv_valid.values, name="OBV",
            line=dict(color="#7c3aed", width=1.6),
            fill="tozeroy", fillcolor="rgba(124,58,237,0.08)",
        ))
        fig_obv.update_layout(
            height=200, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        )
        st.plotly_chart(apply_theme(fig_obv), use_container_width=True)
        st.caption(
            "OBV rośnie gdy cena rośnie na dużym wolumenie, spada gdy spada na dużym. "
            "Dywergencja = cena i OBV idą w różne strony → możliwy sygnał odwrócenia."
        )
    else:
        st.caption("Brak wystarczających danych do wyliczenia OBV.")
with tab2:
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

with tab3:
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

with tab_forecast:
    st.markdown("### 🔮 Scenariusze cenowe (NIE prognoza!)")
    st.error(
        "⚠️ **To nie jest przewidywanie ceny.** Rynki akcji są w dużej "
        "mierze zgodne z hipotezą 'błądzenia losowego' - nikt (włącznie "
        "z tym narzędziem) nie wie, w którą stronę pójdzie cena. "
        "Poniższe wykresy pokazują **zakres możliwych scenariuszy** na "
        "podstawie historycznej zmienności - i jak szybko ten zakres "
        "się rozszerza w czasie. Im dalej w przyszłość, tym mniej to "
        "znaczy."
    )

    horizon = st.select_slider(
        "Horyzont scenariusza",
        options=[7, 14, 30, 60, 90],
        value=30,
        format_func=lambda d: f"{d} dni",
        key=f"horizon_{ticker}",
    )

    with st.spinner("Liczenie scenariuszy..."):
        mc = forecasting.monte_carlo_forecast(df, horizon_days=horizon)
        lt = forecasting.linear_trend_forecast(df, horizon_days=horizon)
        ho = forecasting.holt_forecast(df, horizon_days=horizon)

    if "error" in mc:
        st.warning(mc["error"])
    else:
        stats = mc["stats"]

        # --- wykres "stożka niepewności" ---
        fig_fc = go.Figure()

        # historia (ostatnie ~90 dni) dla kontekstu
        hist_tail = df["Close"].tail(90)
        fig_fc.add_trace(go.Scatter(
            x=hist_tail.index, y=hist_tail.values,
            name="Historia", line=dict(color="#2563eb", width=2),
        ))

        mc_dates = mc["dates"]
        fig_fc.add_trace(go.Scatter(
            x=mc_dates, y=mc["percentiles"][95], line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig_fc.add_trace(go.Scatter(
            x=mc_dates, y=mc["percentiles"][5], line=dict(width=0),
            fill="tonexty", fillcolor="rgba(37,99,235,0.10)",
            name="Zakres 5%-95%", hoverinfo="skip",
        ))
        fig_fc.add_trace(go.Scatter(
            x=mc_dates, y=mc["percentiles"][75], line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig_fc.add_trace(go.Scatter(
            x=mc_dates, y=mc["percentiles"][25], line=dict(width=0),
            fill="tonexty", fillcolor="rgba(37,99,235,0.22)",
            name="Zakres 25%-75%", hoverinfo="skip",
        ))
        fig_fc.add_trace(go.Scatter(
            x=mc_dates, y=mc["percentiles"][50],
            line=dict(color="#2563eb", width=2, dash="dot"),
            name="Mediana (Monte Carlo)",
        ))

        if "error" not in lt:
            fig_fc.add_trace(go.Scatter(
                x=lt["dates"], y=lt["forecast"],
                line=dict(color="#f59e0b", width=2, dash="dash"),
                name="Trend liniowy",
            ))

        if "error" not in ho:
            fig_fc.add_trace(go.Scatter(
                x=ho["dates"], y=ho["forecast"],
                line=dict(color="#7c3aed", width=2, dash="dashdot"),
                name="Wygładzanie Holta",
            ))

        fig_fc.update_layout(
            title=f"Scenariusze ceny na najbliższe {horizon} dni - {ticker}",
            height=450,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            yaxis_title=f"Cena ({wynik['currency']})",
            hovermode="x unified",
        )
        st.plotly_chart(apply_theme(fig_fc), use_container_width=True)

        # --- statystyki ---
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            st.metric("Cena dziś", f"{stats['current_price']:.2f}")
        with col_f2:
            st.metric(
                f"Mediana scenariusza ({horizon}d)",
                f"{stats['median_final']:.2f}",
                delta=f"{(stats['median_final']/stats['current_price']-1)*100:+.1f}%",
            )
        with col_f3:
            st.metric(
                "Zakres 90% (5-95 percentyl)",
                f"{stats['p5_final']:.2f} - {stats['p95_final']:.2f}",
            )
        with col_f4:
            st.metric(
                "Szansa na wzrost",
                f"{stats['prob_up_pct']:.0f}%",
                help="Procent symulowanych ścieżek Monte Carlo, w których "
                     "cena na koniec horyzontu jest wyższa niż dzisiaj.",
            )

        st.markdown(
            f"- {forecasting.interpret_forecast(stats)}\n"
            f"- Zannualizowana **zmienność** (sigma) wynosi "
            f"**{stats['sigma_annualized_pct']:.1f}%** - to główny "
            f"czynnik, który 'rozszerza' zakres scenariuszy. Spółki "
            f"o wyższej zmienności mają szerszy 'stożek niepewności'.\n"
            f"- Szacunki bazują na ostatnich **{stats['lookback_days']} dniach** "
            f"danych historycznych."
        )

        if "error" not in lt:
            kierunek_lt = "wzrostowy" if lt["slope_pct_per_day"] > 0 else "spadkowy"
            st.caption(
                f"📐 Trend liniowy z ostatnich {lt['lookback_days']} dni: "
                f"**{kierunek_lt}**, ~{lt['slope_pct_per_day']:+.2f}%/dzień "
                f"- gdyby utrzymał się bez zmian, prowadziłby do "
                f"{lt['forecast'][-1]:.2f} za {horizon} dni "
                f"(przedział 90%: {lt['lower_90'][-1]:.2f} - {lt['upper_90'][-1]:.2f})."
            )

        # --- histogram rozkładu cen końcowych ---
        with st.expander("📊 Rozkład możliwych cen na koniec horyzontu"):
            fig_hist = go.Figure(go.Histogram(
                x=mc["final_prices"], nbinsx=50,
                marker_color="#2563eb",
            ))
            fig_hist.add_vline(
                x=stats["current_price"], line_dash="dash", line_color="#888",
                annotation_text="Cena dziś",
            )
            fig_hist.update_layout(
                title=f"Rozkład {len(mc['final_prices'])} symulowanych cen za {horizon} dni",
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis_title=f"Cena ({wynik['currency']})",
                showlegend=False,
            )
            st.plotly_chart(apply_theme(fig_hist), use_container_width=True)

    st.divider()
    st.markdown(
        """
        #### Jak czytać ten wykres?

        - **Niebieski obszar** to nie "korytarz", w którym cena
          'musi' się znaleźć - to symulacja tysięcy losowych ścieżek
          opartych na historycznej zmienności. Ciemniejszy obszar
          (25-75%) to gdzie skończyła się **połowa** symulacji,
          jasny (5-95%) to **90%** symulacji.
        - **Linia trendu** i **Holt** to ekstrapolacje ostatniego
          kierunku ceny - przydatne do zrozumienia "co by było, gdyby
          nic się nie zmieniło", ale rynki regularnie "zmieniają coś".
        - Zauważ, jak szybko obszar niepewności się **rozszerza** -
          to nie błąd modelu, to rzeczywistość: im dalej w przyszłość,
          tym mniej można powiedzieć z sensowną pewnością.

        #### Do czego to się NADAJE
        - Zrozumienia, jak duża może być wahania ceny w danym okresie
          (np. "czy mogę stracić 20% w miesiąc, nawet przy dobrym
          wyniku score?").
        - Porównania zmienności różnych spółek (szerszy stożek =
          bardziej ryzykowna spółka).

        #### Do czego się NIE nadaje
        - Decydowania "kupić czy sprzedać" na podstawie tego, gdzie
          wypada mediana.
        - Traktowania granic 5%/95% jako "gwarantowanych" - rzeczywiste
          ceny czasem wychodzą poza te zakresy (tzw. "tłuste ogony"
          rozkładów finansowych).
        """
    )

with tab4:
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

with tab5:
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

with tab6:
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
