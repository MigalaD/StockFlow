# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
O aplikacji
============
Strona informacyjna: czym jest narzędzie, czym NIE jest, skąd dane,
jak czytać wynik. Ważna przy publicznym wdrożeniu (zaufanie + disclaimer).
"""
import streamlit as st
from common import footer, sidebar_user, sidebar_legenda, beta_banner, FEEDBACK_URL

user_id = sidebar_user()
sidebar_legenda()

st.title("ℹ️ O aplikacji")
beta_banner()

st.markdown("""
### Co to jest?

**Analizator Spółek** to narzędzie **edukacyjne i analityczne**, które dla
spółek, ETF-ów, kryptowalut i surowców liczy zbiorczy „wynik" (0–100) na
podstawie sygnałów technicznych i fundamentalnych. Pomaga szybciej zrozumieć
sytuację instrumentu i porównać kilka naraz.

### Czym to **NIE** jest

- ❌ **To nie jest porada inwestycyjna** ani rekomendacja kupna/sprzedaży.
- ❌ Wynik **nie przewiduje** przyszłej ceny – opisuje obecną sytuację.
- ❌ To nie jest narzędzie do automatycznego handlu.

Wysoki wynik **nie znaczy „kup"**, a niski **nie znaczy „sprzedaj"**. To punkt
wyjścia do własnej analizy, nie jej zakończenie. Decyzje inwestycyjne
podejmujesz na własną odpowiedzialność.

### Skąd pochodzą dane?

Dane rynkowe pobieramy z **Yahoo Finance** (przez bibliotekę `yfinance`).
Mogą być opóźnione, niekompletne lub chwilowo niedostępne. Nie gwarantujemy
ich poprawności.

### Jak czytać wynik (score)?

- 🟢 **60–100** – przewaga sygnałów „pozytywnych"
- ⚪ **40–60** – brak wyraźnego sygnału
- 🔴 **0–40** – przewaga sygnałów „negatywnych"

Wynik to **ważona średnia** ~10 wskaźników (trend, RSI, MACD, wolumen,
zmienność, wycena, momentum, dywidenda, sentyment newsów, fundamenty).
Wagi i szczegóły każdego wskaźnika zobaczysz w zakładce **Analiza** →
„Szczegóły wyniku" oraz „Co to znaczy?".

### Prywatność i dane

„Nazwa użytkownika" w panelu bocznym to **tylko etykieta** do rozdzielenia
watchlist – **nie** jest zabezpieczona hasłem. Nie wpisuj tam danych
wrażliwych. W wersji testowej dane mogą zostać zresetowane.
""")

st.divider()
st.markdown("### 💬 Masz uwagi lub znalazłeś błąd?")
st.markdown(
    f"Będziemy wdzięczni za feedback w trakcie testów. "
    f"[**Zgłoś uwagę lub błąd →**]({FEEDBACK_URL})"
)

footer(pokaz_feedback=False)
