"""
Ustawienia
"""
import streamlit as st
from common import (
    footer,
    sidebar_legenda,
    sidebar_user,
)
from stock_analyzer import analyze_ticker
from email_alerts import check_and_send_email_alerts, send_daily_digest, send_email
from telegram_alerts import check_and_send_alerts, default_thresholds, send_telegram_message
import database as db

user_id = sidebar_user()
sidebar_legenda()

st.title("⚙️ Ustawienia")
st.markdown(f"Konfiguracja dla użytkownika: **{user_id}**.")

tab_tg, tab_email, tab_wyglad, tab_diag = st.tabs([
    "📱 Telegram", "✉️ E-mail", "🌓 Wygląd", "🩺 Diagnostyka",
])

# ----------------------------------------------------------
# TELEGRAM
# ----------------------------------------------------------
with tab_tg:
    from secrets_util import is_encryption_active
    if is_encryption_active():
        st.caption("🔒 Token jest szyfrowany w bazie (Fernet).")
    else:
        st.warning(
            "⚠️ Szyfrowanie sekretów nieaktywne (brak ENCRYPTION_KEY). "
            "Token zostanie zapisany **jawnie**. Na publicznym wdrożeniu "
            "ustaw ENCRYPTION_KEY w sekretach Streamlit Cloud."
        )
    st.markdown(
        "Gdy spółka z Twojej watchlist przekroczy ustawiony próg "
        "wyniku, dostaniesz wiadomość na Telegramie (jeśli "
        "`scheduler.py` jest uruchamiany regularnie - patrz instrukcja "
        "w `scheduler.py`)."
    )

    with st.expander("📋 Jak skonfigurować bota Telegram (krok po kroku)", expanded=False):
        st.markdown(
            """
            1. W aplikacji Telegram znajdź **@BotFather** i wyślij mu `/newbot`.
               Postępuj według instrukcji - na koniec dostaniesz **TOKEN**
               (ciąg znaków w stylu `123456789:ABCdefGhIJKlmnoPQRsTUVwxyz`).
            2. Znajdź swojego nowo utworzonego bota w Telegramie i wyślij mu
               jakąkolwiek wiadomość (np. "cześć") - bot musi mieć z Tobą
               rozpoczętą rozmowę, żeby mógł Ci pisać.
            3. W przeglądarce otwórz adres (zamień `<TOKEN>` na swój token):

               `https://api.telegram.org/bot<TOKEN>/getUpdates`

               Znajdź w odpowiedzi fragment `"chat":{"id": ...}` - liczba
               po `"id":` to Twój **CHAT_ID**.
            4. Wklej TOKEN i CHAT_ID poniżej i zapisz.
            5. Kliknij "Wyślij testowe powiadomienie", żeby sprawdzić,
               czy wszystko działa.
            """
        )

    current_tg = db.get_telegram_settings(user_id) or {}

    with st.form("telegram_settings"):
        token = st.text_input(
            "Token bota", value=current_tg.get("telegram_token") or "",
            type="password",
            help="Token otrzymany od @BotFather.",
        )
        chat_id = st.text_input(
            "Chat ID", value=current_tg.get("telegram_chat_id") or "",
            help="Twój numeryczny identyfikator czatu z botem.",
        )
        zapisz_tg = st.form_submit_button("💾 Zapisz ustawienia Telegram", type="primary")

    if zapisz_tg:
        db.save_telegram_settings(user_id, token.strip(), chat_id.strip())
        st.success("Ustawienia zapisane.")

    if current_tg.get("telegram_token") and current_tg.get("telegram_chat_id"):
        col_tg1, col_tg2 = st.columns(2)
        with col_tg1:
            if st.button("📨 Wyślij testowe powiadomienie", key="tg_test"):
                ok, msg = send_telegram_message(
                    current_tg["telegram_token"], current_tg["telegram_chat_id"],
                    f"✅ Test powiadomień z Analizatora Spółek (użytkownik: {user_id}).",
                )
                if ok:
                    st.success("Wiadomość wysłana - sprawdź Telegram!")
                else:
                    st.error(f"Nie udało się wysłać: {msg}")
        with col_tg2:
            if st.button("🔔 Sprawdź watchlist i wyślij alerty", key="tg_check"):
                with st.spinner("Sprawdzanie..."):
                    log = check_and_send_alerts(user_id, analyze_ticker)
                for line in log:
                    st.write(line)

# ----------------------------------------------------------
# EMAIL
# ----------------------------------------------------------
with tab_email:
    st.markdown(
        "Alternatywa dla Telegrama - alerty i codzienne podsumowania "
        "watchlist wysyłane na e-mail przez SMTP. Większość skrzynek "
        "wymaga **hasła aplikacji** (App Password), nie zwykłego "
        "hasła konta."
    )

    with st.expander("📋 Jak skonfigurować e-mail (Gmail - krok po kroku)", expanded=False):
        st.markdown(
            """
            1. Włącz weryfikację dwuetapową na koncie Google
               (Konto Google -> Bezpieczeństwo).
            2. Wejdź na **myaccount.google.com/apppasswords** i
               wygeneruj "hasło aplikacji" (16 znaków, bez spacji).
            3. Wpisz poniżej:
               - SMTP server: `smtp.gmail.com`
               - SMTP port: `587`
               - E-mail (login): Twój adres Gmail
               - Hasło: wygenerowane hasło aplikacji (NIE zwykłe hasło)
               - Adres docelowy: gdzie wysyłać powiadomienia (może być
                 ten sam adres)

            Inne popularne SMTP: Outlook/Office365 -
            `smtp.office365.com:587`, Yahoo - `smtp.mail.yahoo.com:587`.
            """
        )

    current_email = db.get_email_settings(user_id) or {}

    with st.form("email_settings"):
        col_e1, col_e2 = st.columns([3, 1])
        with col_e1:
            smtp_server = st.text_input(
                "SMTP server", value=current_email.get("email_smtp_server") or "smtp.gmail.com",
            )
        with col_e2:
            smtp_port = st.number_input(
                "Port", value=int(current_email.get("email_smtp_port") or 587), step=1,
            )
        email_user = st.text_input(
            "E-mail (login)", value=current_email.get("email_user") or "",
        )
        email_password = st.text_input(
            "Hasło aplikacji", value=current_email.get("email_password") or "",
            type="password",
            help="Hasło aplikacji (App Password), nie zwykłe hasło konta.",
        )
        email_to = st.text_input(
            "Wyślij powiadomienia na adres",
            value=current_email.get("email_to") or "",
            help="Może być ten sam adres co login.",
        )
        zapisz_email = st.form_submit_button("💾 Zapisz ustawienia e-mail", type="primary")

    if zapisz_email:
        db.save_email_settings(
            user_id, smtp_server.strip(), int(smtp_port),
            email_user.strip(), email_password, email_to.strip(),
        )
        st.success("Ustawienia zapisane.")

    current_email = db.get_email_settings(user_id) or {}
    if current_email.get("email_to") and current_email.get("email_smtp_server"):
        col_em1, col_em2, col_em3 = st.columns(3)
        with col_em1:
            if st.button("📨 Wyślij testowy e-mail", key="email_test"):
                ok, msg = send_email(
                    current_email["email_smtp_server"], current_email["email_smtp_port"],
                    current_email["email_user"], current_email["email_password"],
                    current_email["email_to"], "✅ Test - Analizator Spółek",
                    f"To jest testowa wiadomość (użytkownik: {user_id}).",
                )
                if ok:
                    st.success("E-mail wysłany - sprawdź skrzynkę!")
                else:
                    st.error(f"Nie udało się wysłać: {msg}")
        with col_em2:
            if st.button("🔔 Sprawdź watchlist i wyślij alerty", key="email_check"):
                with st.spinner("Sprawdzanie..."):
                    log = check_and_send_email_alerts(user_id, analyze_ticker)
                for line in log:
                    st.write(line)
        with col_em3:
            if st.button("📋 Wyślij podsumowanie watchlist teraz", key="email_digest"):
                with st.spinner("Wysyłanie..."):
                    ok, msg = send_daily_digest(user_id, analyze_ticker)
                if ok:
                    st.success("Podsumowanie wysłane!")
                else:
                    st.error(f"Nie udało się wysłać: {msg}")

# ----------------------------------------------------------
# WSPÓLNE INFO O ALERTACH + WYGLĄD
# ----------------------------------------------------------
st.divider()
default_high, default_low = default_thresholds()
st.markdown(
    f"""
    #### Jak działają alerty?

    - Domyślne progi: alert gdy wynik spółki ≥ **{default_high:.0f}**
      (sygnał pozytywny) lub ≤ **{default_low:.0f}** (sygnał negatywny).
    - Możesz ustawić własne progi dla każdej spółki w zakładce
      '⭐ Watchlist'.
    - Każdy alert wysyłany jest **maksymalnie raz dziennie** dla danej
      spółki i typu alertu, żeby nie zalewać Cię powiadomieniami.
    - Alerty wymagają uruchamiania `scheduler.py` (np. raz dziennie
      przez Harmonogram zadań Windows / cron) - inaczej alerty są
      wysyłane tylko wtedy, gdy klikniesz odpowiedni przycisk powyżej.
    - Możesz skonfigurować **oba kanały naraz** (Telegram + e-mail) -
      `scheduler.py` sprawdzi i wyśle przez wszystkie skonfigurowane.
    """
)

with tab_wyglad:
    st.markdown("#### 🌓 Tryb ciemny / jasny")
    st.markdown(
        "Wygląd strony możesz zmienić rozwijając opcję w prawnym górnym rogu Streamlit."
    )

    st.divider()
    st.markdown("#### 🗄️ Lokalny cache danych cenowych")
    st.markdown(
        "Dane cenowe (historia notowań) są zapisywane lokalnie na "
        "15 minut, żeby przyspieszyć ładowanie i ograniczyć liczbę "
        "zapytań do Yahoo Finance - dotyczy to **wszystkich** "
        "użytkowników tej instalacji (cache jest współdzielony)."
    )
    cache_stats = db.get_price_cache_stats()
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("Zapisane zestawy danych", cache_stats.get("n") or 0)
    with col_c2:
        oldest = cache_stats.get("oldest")
        st.metric("Najstarszy wpis", oldest[:19].replace("T", " ") if oldest else "-")
    with col_c3:
        newest = cache_stats.get("newest")
        st.metric("Najnowszy wpis", newest[:19].replace("T", " ") if newest else "-")

    if st.button("🗑️ Wyczyść cache cen"):
        db.clear_price_cache()
        st.success("Cache wyczyszczony - następne wczytanie danych będzie wolniejsze.")
        st.rerun()


with tab_diag:
    st.markdown("#### 🩺 Dziennik zdarzeń aplikacji")
    st.markdown(
        "Ostatnie wpisy z logów aplikacji – błędy analizy, wykryte "
        "ograniczenia tempa (rate-limit 429), czas trwania skanów. "
        "Przydatne, gdy coś działa nie tak, jak powinno."
    )
    from app_logging import read_recent_logs, get_log_file_path

    n_lines = st.slider("Ile ostatnich linii pokazać", 20, 500, 100, step=20)
    logi = read_recent_logs(n_lines)
    if not logi:
        st.info("Brak wpisów w logu (lub plik jeszcze nie powstał).")
    else:
        st.code("\n".join(logi), language="log")
        st.caption(f"Plik logu: `{get_log_file_path()}`")


footer()
