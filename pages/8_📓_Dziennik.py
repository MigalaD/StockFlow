"""
Dziennik inwestycyjny
"""
import streamlit as st
import pandas as pd
from common import (
    footer,
    pobierz_analize,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import interpret_score
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("📓 Dziennik")
st.markdown(
    "Zapisuj swoje decyzje i rozumowanie - co kupiłeś/sprzedałeś (albo "
    "dlaczego zdecydowałeś się NIC nie robić), i jaki był wynik (score) "
    "i cena spółki w tamtym momencie. Po czasie możesz wrócić i "
    "sprawdzić, czy Twoje rozumowanie się sprawdzało."
)

DECYZJE = ["Kupno", "Sprzedaż", "Obserwacja", "Zwiększenie pozycji",
           "Zmniejszenie pozycji", "Bez zmian (HOLD)", "Inne"]

with st.form("dodaj_wpis_dziennika", clear_on_submit=True):
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        wpis_data = st.date_input("Data")
    with col_b:
        wpis_ticker = st.text_input("Symbol (opcjonalnie)", placeholder="np. AAPL")
    with col_c:
        wpis_decyzja = st.selectbox("Decyzja", DECYZJE)

    wpis_powod = st.text_area(
        "Powód / rozumowanie",
        placeholder="np. Wynik wzrósł do 75/100, trend wzrostowy potwierdzony "
                    "przez MACD, dodaję do watchlist i obserwuję.",
    )

    col_d, col_e = st.columns(2)
    with col_d:
        wpis_uzyj_score = st.checkbox(
            "Pobierz aktualny wynik i cenę dla tego symbolu",
            value=True,
            help="Jeśli zaznaczone, dashboard sprawdzi obecny score i "
                 "cenę dla podanego symbolu i zapisze je razem z wpisem.",
        )

    dodaj_wpis = st.form_submit_button("➕ Dodaj wpis", type="primary")

if dodaj_wpis:
    score_at_entry = None
    price_at_entry = None
    if wpis_uzyj_score and wpis_ticker.strip():
        try:
            res_journal = pobierz_analize(wpis_ticker.strip().upper())
            if "error" not in res_journal:
                score_at_entry = res_journal["total_score"]
                price_at_entry = res_journal["price"]
        except Exception:
            pass

    db.add_journal_entry(
        user_id, wpis_data.isoformat(),
        wpis_ticker.strip().upper() if wpis_ticker.strip() else None,
        wpis_decyzja, wpis_powod.strip(),
        score_at_entry, price_at_entry,
    )
    st.success("Wpis dodany do dziennika.")

st.divider()

filtr_ticker = st.text_input(
    "🔎 Filtruj po symbolu (opcjonalnie)", placeholder="np. AAPL",
    key="journal_filter",
).strip().upper()

wpisy = db.get_journal_entries(user_id, ticker=filtr_ticker or None)

if not wpisy:
    st.info("Brak wpisów w dzienniku. Dodaj pierwszy powyżej.")
    st.stop()

for w in wpisy:
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.markdown(f"**{w['entry_date']}**")
        if w["ticker"]:
            st.caption(f"🏷️ {w['ticker']}")
    with col2:
        st.markdown(f"**{w['decision']}**")
        if w["reason"]:
            st.write(w["reason"])
        if w["score_at_entry"] is not None:
            st.caption(
                f"Wynik w momencie wpisu: {w['score_at_entry']:.0f}/100 "
                f"({interpret_score(w['score_at_entry'])}) • "
                f"Cena: {w['price_at_entry']}"
            )

            # porównanie ze stanem obecnym, jeśli mamy ticker
            if w["ticker"]:
                try:
                    aktualny = pobierz_analize(w["ticker"])
                    if "error" not in aktualny:
                        zmiana_ceny = (aktualny["price"] / w["price_at_entry"] - 1) * 100 \
                            if w["price_at_entry"] else None
                        zmiana_score = aktualny["total_score"] - w["score_at_entry"]
                        bits = []
                        if zmiana_ceny is not None:
                            bits.append(f"cena {zmiana_ceny:+.1f}%")
                        bits.append(f"score {zmiana_score:+.1f}")
                        st.caption(f"📊 Od tego wpisu: {', '.join(bits)} (dziś: {aktualny['total_score']:.0f}/100)")
                except Exception:
                    pass
    with col3:
        if st.button("🗑️", key=f"del_journal_{w['id']}"):
            db.delete_journal_entry(w["id"], user_id)
            st.rerun()
    st.divider()

journal_df = pd.DataFrame(wpisy)
if not journal_df.empty:
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        csv = journal_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Pobierz dziennik jako CSV",
            data=csv, file_name="dziennik.csv", mime="text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        from excel_export import build_workbook, suggested_filename
        xlsx_bytes = build_workbook(journal_rows=wpisy)
        st.download_button(
            "⬇️ Pobierz dziennik (Excel)",
            data=xlsx_bytes,
            file_name=suggested_filename("dziennik"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )



footer()
