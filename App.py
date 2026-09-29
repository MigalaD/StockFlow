# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
app.py – strona główna (Dashboard) StockFlow
"""
import streamlit as st
import yfinance as yf
from datetime import datetime

from common import (
    KOLOR_DOBRY, KOLOR_SLABY, KOLOR_AKCENTU, KOLOR_NEUTRALNY,
    KOLOR_TEKST, KOLOR_TLO2,
    APP_VERSION,
    pobierz_analize, emoji_dla_score, kolor_dla_score,
    footer, sidebar_user, sidebar_legenda,
    section_header, empty_state, karta_watchlist,
)
import database as db

st.set_page_config(
    page_title="StockFlow – Analityka Rynkowa",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/migalad/stockflow",
        "Report a bug": "https://github.com/migalad/stockflow/issues",
        "About": "StockFlow v" + "1.1.0" + " — narzędzie edukacyjne do analizy rynkowej.",
    },
)

# Mobile meta tags — theme-color dla paska przeglądarki na mobile
st.markdown(
    """
    <meta name="theme-color" content="#1F2937">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    """,
    unsafe_allow_html=True,
)

user_id = sidebar_user()
sidebar_legenda()

# ── 3. Onboarding flow dla nowego użytkownika ─────────────────────────
_ONBOARDED_KEY = f"_onboarded_{user_id}"

def _pokaz_onboarding():
    """Trzystopniowy przewodnik dla nowego użytkownika."""
    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding: 40px 20px 20px 20px;
            font-family: Inter, sans-serif;
        ">
          <div style="font-size:2.5rem; margin-bottom:12px;">📈</div>
          <div style="
            font-size:1.6rem; font-weight:700;
            color:{KOLOR_TEKST}; margin-bottom:6px;
          ">Witaj w StockFlow!</div>
          <div style="
            font-size:0.95rem; color:{KOLOR_NEUTRALNY};
            max-width:480px; margin:0 auto 28px auto;
          ">
            Narzędzie do analizy technicznej i fundamentalnej akcji,
            ETF-ów, kryptowalut i surowców. Zacznij w 3 krokach:
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    steps = [
        ("1️⃣", "Wybierz instrument",
         "Przejdź do strony **📈 Analiza** i wpisz symbol spółki, "
         "ETF-u lub kryptowaluty (np. AAPL, CDR.WA, BTC-USD).",
         KOLOR_DOBRY),
        ("2️⃣", "Przeczytaj wynik",
         "Aplikacja obliczy **Score 0–100** — im wyższy, tym więcej "
         "wskaźników technicznych i fundamentalnych jest pozytywnych. "
         "To **nie** jest porada inwestycyjna.",
         KOLOR_AKCENTU),
        ("3️⃣", "Obserwuj i porównuj",
         "Dodaj spółki do **⭐ Watchlisty**, śledź zmiany, "
         "porównuj instrumenty i uruchom **🔍 Skaner** rynku.",
         "#3B82F6"),
    ]

    for col, (numer, tytul, opis, kolor) in zip([col1, col2, col3], steps):
        with col:
            st.markdown(
                f"""
                <div style="
                    background: {kolor}0D;
                    border: 1px solid {kolor}30;
                    border-top: 3px solid {kolor};
                    border-radius: 12px;
                    padding: 20px 18px;
                    font-family: Inter, sans-serif;
                    height: 100%;
                ">
                  <div style="font-size:1.6rem; margin-bottom:8px;">{numer}</div>
                  <div style="font-weight:700; font-size:0.95rem;
                              color:{KOLOR_TEKST}; margin-bottom:8px;">
                    {tytul}
                  </div>
                  <div style="font-size:0.83rem; color:{KOLOR_NEUTRALNY};
                              line-height:1.5;">
                    {opis}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("")
    col_btn, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        if st.button(
            "✅ Rozumiem — przejdź do dashboardu",
            use_container_width=True,
            type="primary",
        ):
            st.session_state[_ONBOARDED_KEY] = True
            st.rerun()

    st.caption(
        "ℹ️ StockFlow to narzędzie edukacyjne — nie stanowi porady inwestycyjnej. "
        "Wszystkie wyniki i sygnały służą wyłącznie do nauki i analizy.",
        help="Pełny disclaimer w zakładce 'O aplikacji'",
    )
    st.stop()

# Pokaż onboarding tylko nowym użytkownikom (pierwsza wizyta w sesji)
# Wykrywamy "nowego" po pustej watchliście I braku flagi sesyjnej.
_watchlist_check = db.get_watchlist(user_id)
_jest_nowy = (
    not _watchlist_check
    and not st.session_state.get(_ONBOARDED_KEY, False)
    and user_id == "default"  # nie przerywaj onboardingiem custom userów
)
if _jest_nowy:
    _pokaz_onboarding()
    # st.stop() jest wewnątrz _pokaz_onboarding jeśli nie kliknął przycisku

# ── Hero nagłówek ─────────────────────────────────────────────────────
hora = datetime.now().hour
powitanie = "Dzień dobry" if hora < 12 else "Witaj" if hora < 18 else "Dobry wieczór"

st.markdown(
    f"""
    <div style="padding:8px 0 20px 0; font-family:Inter,sans-serif;">
      <div style="font-size:1.6rem; font-weight:700; color:{KOLOR_TEKST};">
        {powitanie}, <span style="color:{KOLOR_DOBRY};">{user_id}</span> 👋
      </div>
      <div style="font-size:0.9rem; color:{KOLOR_NEUTRALNY}; margin-top:4px;">
        StockFlow &nbsp;·&nbsp; v{APP_VERSION} &nbsp;·&nbsp;
        {datetime.now().strftime('%d %b %Y, %H:%M')}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── VIX baner ────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def get_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        if df.empty:
            return None, None
        current = float(df["Close"].iloc[-1])
        prev    = float(df["Close"].iloc[-2]) if len(df) > 1 else current
        return current, current - prev
    except Exception:
        return None, None

vix_val, vix_delta = get_vix()

col_vix, col_nav1, col_nav2, col_nav3 = st.columns([1.4, 1, 1, 1])

with col_vix:
    if vix_val is not None:
        if vix_val < 15:
            vix_label, vix_color, vix_emoji = "Spokój rynkowy", KOLOR_DOBRY, "😌"
        elif vix_val < 25:
            vix_label, vix_color, vix_emoji = "Normalna zmienność", "#F59E0B", "😐"
        elif vix_val < 35:
            vix_label, vix_color, vix_emoji = "Podwyższona niepewność", "#E07800", "😟"
        else:
            vix_label, vix_color, vix_emoji = "Wysoki strach / panika", KOLOR_SLABY, "😱"

        st.markdown(
            f"""
            <div style="
                background:{vix_color}14;
                border:1px solid {vix_color}40;
                border-radius:12px;
                padding:14px 18px;
                font-family:Inter,sans-serif;
            ">
              <div style="font-size:0.75rem;opacity:0.55;text-transform:uppercase;
                          letter-spacing:0.06em;margin-bottom:4px;">
                VIX – Indeks strachu
              </div>
              <div style="display:flex;align-items:baseline;gap:8px;">
                <span style="font-size:2rem;font-weight:700;
                             color:{vix_color};">{vix_val:.1f}</span>
                <span style="font-size:0.9rem;color:{vix_color};opacity:0.8;">
                    {vix_delta:+.2f}
                </span>
                <span style="font-size:1.2rem;">{vix_emoji}</span>
              </div>
              <div style="font-size:0.82rem;opacity:0.65;margin-top:2px;">
                {vix_label}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("VIX niedostępny")

# Skróty nawigacyjne jako mini-karty
for col, ikona, tytul, opis in [
    (col_nav1, "📈", "Analiza", "Szczegółowa analiza jednej spółki"),
    (col_nav2, "🔍", "Skaner", "Skan rynku USA / GPW / Krypto"),
    (col_nav3, "💼", "Portfolio", "P&L i alokacja Twoich pozycji"),
]:
    with col:
        st.markdown(
            f"""
            <div style="
                background:rgba(255,255,255,0.03);
                border:1px solid rgba(255,255,255,0.07);
                border-radius:12px;
                padding:14px 18px;
                font-family:Inter,sans-serif;
                height:100%;
            ">
              <div style="font-size:1.4rem;margin-bottom:4px;">{ikona}</div>
              <div style="font-weight:600;font-size:0.95rem;">{tytul}</div>
              <div style="font-size:0.78rem;opacity:0.5;margin-top:2px;">{opis}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")

# ── Watchlist dashboard ───────────────────────────────────────────────
section_header("Twoja Watchlist", "⭐",
               "Wyniki odświeżane przy każdym wejściu na stronę")

watchlist = db.get_watchlist(user_id)

if not watchlist:
    # E: Empty state z onboardingiem
    st.markdown("")
    empty_state(
        "⭐",
        "Watchlist jest pusta",
        "Dodaj spółki które chcesz obserwować, "
        "aby zobaczyć ich wyniki i zmiany score w jednym miejscu.",
    )
    st.markdown(
        "<div style='text-align:center;margin-top:4px;"
        "font-family:Inter,sans-serif;font-size:0.88rem;"
        f"color:{KOLOR_NEUTRALNY};'>Zacznij od popularnych instrumentów:</div>",
        unsafe_allow_html=True,
    )
    startery = {
        "🍎 Apple": "AAPL", "🪟 Microsoft": "MSFT",
        "🔍 Alphabet": "GOOGL", "🎮 CD Projekt": "CDR.WA",
        "🏦 PKO BP": "PKO.WA", "₿ Bitcoin": "BTC-USD",
    }
    cols = st.columns(3)
    for i, (label, tk) in enumerate(startery.items()):
        with cols[i % 3]:
            if st.button(label, key=f"onb_{tk}", use_container_width=True):
                db.add_to_watchlist(tk, user_id)
                st.success(f"Dodano {tk}!")
                st.rerun()
else:
    # Pobierz dane watchlisty
    zmiany = []
    prog = st.progress(0, text="Sprawdzam watchlistę…")
    n_total = len(watchlist)
    for i, entry in enumerate(watchlist):
        ticker = entry["ticker"]
        prog.progress(
            int((i + 1) / n_total * 100),
            text=f"Analizuję {ticker} ({i+1}/{n_total})…",
        )
        try:
            wynik = pobierz_analize(ticker)
        except Exception:
            continue
        if "error" in wynik:
            continue
        nowy  = wynik["total_score"]
        stary = entry.get("last_score")
        delta = (nowy - stary) if stary is not None else None
        zmiany.append({
            "ticker":   ticker,
            "name":     wynik["name"],
            "score":    nowy,
            "score_st": wynik.get("score_st"),
            "delta":    delta,
            "price":    wynik["price"],
            "currency": wynik["currency"],
            "sector":   wynik.get("sector", ""),
        })
    prog.empty()

    if not zmiany:
        empty_state("📡", "Nie udało się pobrać danych",
                    "Yahoo Finance może mieć chwilowy problem. Spróbuj za chwilę.")
    else:
        zmiany.sort(key=lambda x: -(abs(x["delta"]) if x["delta"] else 0))

        # Podsumowanie w 4 metrykach
        top4 = zmiany[:4]
        cols = st.columns(len(top4))
        for i, z in enumerate(top4):
            with cols[i]:
                delta_str = f"{z['delta']:+.1f} pkt" if z["delta"] is not None else None
                st.metric(
                    label=f"{emoji_dla_score(z['score'])} {z['ticker']}",
                    value=f"{z['score']:.0f}/100",
                    delta=delta_str,
                    help=f"{z['name']} · Cena: {z['price']} {z['currency']}",
                )

        # Alerty — największe zmiany
        duze = [z for z in zmiany if z["delta"] is not None and abs(z["delta"]) >= 3]
        if duze:
            st.markdown("")
            section_header("Największe zmiany od ostatniej wizyty", "🔔")
            for z in duze[:4]:
                ikona_dir = "📈" if z["delta"] > 0 else "📉"
                kolor     = KOLOR_DOBRY if z["delta"] > 0 else KOLOR_SLABY
                st.markdown(
                    f"<span style='font-family:Inter,sans-serif;'>"
                    f"{ikona_dir} <strong>{z['ticker']}</strong> "
                    f"<span style='opacity:0.6;font-size:0.88rem;'>{z['name']}</span> "
                    f"<span style='color:{kolor};font-weight:600;'>"
                    f"{z['delta']:+.1f} pkt → {z['score']:.0f}/100</span></span>",
                    unsafe_allow_html=True,
                )

        # Pełna lista kart
        st.markdown("")
        section_header("Wszystkie pozycje", "📋")
        col_l, col_r = st.columns(2)
        for i, z in enumerate(zmiany):
            with (col_l if i % 2 == 0 else col_r):
                karta_watchlist(
                    ticker=z["ticker"], name=z["name"],
                    score=z["score"], score_st=z.get("score_st"),
                    price=z["price"], currency=z["currency"],
                    delta=z["delta"], sektor=z.get("sector", ""),
                )

# ── Ostatni skan ──────────────────────────────────────────────────────
st.write("")
section_header("Ostatni skan rynku", "🔍")

last_scan = db.get_last_scan_time()
if not last_scan:
    empty_state(
        "🔍",
        "Skan nie był jeszcze uruchamiany",
        "Przejdź do strony Skaner rynku, aby przeskanować USA, GPW, Europę lub Krypto.",
    )
else:
    scan_dt = last_scan[:19].replace("T", " ")
    results = db.get_scan_results()
    if results:
        import pandas as pd

        df_scan = pd.DataFrame(results).sort_values("score", ascending=False)

        # Top 5 i Bottom 5 obok siebie
        col_top, col_bot = st.columns(2)
        with col_top:
            st.markdown(
                f"<div style='font-family:Inter,sans-serif;font-size:0.82rem;"
                f"font-weight:600;color:{KOLOR_DOBRY};margin-bottom:6px;'>"
                f"🟢 TOP 5</div>",
                unsafe_allow_html=True,
            )
            for _, row in df_scan.head(5).iterrows():
                kolor = kolor_dla_score(row["score"])
                st.markdown(
                    f"<div style='font-family:Inter,sans-serif;"
                    f"display:flex;justify-content:space-between;"
                    f"padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.05);'>"
                    f"<span><strong>{row['ticker']}</strong> "
                    f"<span style='opacity:0.5;font-size:0.8rem;'>{(row.get('name') or '')[:22]}</span></span>"
                    f"<span style='color:{kolor};font-weight:700;'>{row['score']:.0f}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        with col_bot:
            st.markdown(
                f"<div style='font-family:Inter,sans-serif;font-size:0.82rem;"
                f"font-weight:600;color:{KOLOR_SLABY};margin-bottom:6px;'>"
                f"🔴 BOTTOM 5</div>",
                unsafe_allow_html=True,
            )
            for _, row in df_scan.tail(5).iterrows():
                kolor = kolor_dla_score(row["score"])
                st.markdown(
                    f"<div style='font-family:Inter,sans-serif;"
                    f"display:flex;justify-content:space-between;"
                    f"padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.05);'>"
                    f"<span><strong>{row['ticker']}</strong> "
                    f"<span style='opacity:0.5;font-size:0.8rem;'>{(row.get('name') or '')[:22]}</span></span>"
                    f"<span style='color:{kolor};font-weight:700;'>{row['score']:.0f}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.caption(f"Skan z {scan_dt} · {len(results)} instrumentów")

footer()
