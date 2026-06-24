# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Powiadomienia E-mail
======================
Alternatywa dla Telegrama - wysyła alerty / podsumowania na e-mail przez
SMTP. Działa z większością skrzynek (Gmail, Outlook, własna domena),
ale wymaga "hasła aplikacji" (App Password), nie zwykłego hasła do konta
(większość dostawców wymaga tego dla bezpieczeństwa).

Jak skonfigurować dla Gmaila (instrukcja również w dashboardzie):
1. Włącz weryfikację dwuetapową na koncie Google.
2. Wejdź na https://myaccount.google.com/apppasswords i wygeneruj
   "hasło aplikacji" (16 znaków).
3. W zakładce "Ustawienia" dashboardu wpisz:
   - SMTP server: smtp.gmail.com
   - SMTP port: 587
   - Email użytkownika: twoj.email@gmail.com
   - Hasło: wygenerowane hasło aplikacji (NIE Twoje normalne hasło)
   - Adres docelowy: gdzie wysyłać powiadomienia (może być ten sam adres)

Inne popularne SMTP:
- Outlook/Office365: smtp.office365.com, port 587
- Yahoo: smtp.mail.yahoo.com, port 587
"""

from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import database as db


def send_email(smtp_server: str, smtp_port: int, email_user: str, email_password: str,
                email_to: str, subject: str, body: str) -> tuple[bool, str]:
    """Wysyła e-mail przez SMTP (STARTTLS). Zwraca (sukces, komunikat_błędu_lub_OK)."""
    if not all([smtp_server, smtp_port, email_user, email_password, email_to]):
        return False, "Niekompletna konfiguracja e-mail."

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, int(smtp_port), timeout=15) as server:
            server.starttls(context=context)
            server.login(email_user, email_password)
            server.sendmail(email_user, email_to, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_and_send_email_alerts(user_id: str, analyze_fn) -> list[str]:
    """
    Sprawdza watchlist danego użytkownika i wysyła e-mail, gdy score
    przekroczy ustawiony próg (analogicznie do alertów Telegram).
    Każdy alert wysyłany jest maksymalnie raz dziennie (wspólny log
    alert_log z Telegramem - jeśli oba kanały są skonfigurowane,
    użytkownik dostanie powiadomienie tylko jednym z nich; pierwszy,
    który zostanie sprawdzony, "zajmuje" log na ten dzień).
    """
    log = []
    settings = db.get_email_settings(user_id)
    if not settings or not settings.get("email_to") or not settings.get("email_smtp_server"):
        return [f"[{user_id}] E-mail nieskonfigurowany - pomijam."]

    watchlist = db.get_watchlist(user_id)
    default_high, default_low = 70.0, 30.0

    for entry in watchlist:
        ticker = entry["ticker"]
        try:
            res = analyze_fn(ticker)
        except Exception as e:
            log.append(f"[{user_id}] {ticker}: błąd analizy ({e})")
            continue

        if "error" in res:
            log.append(f"[{user_id}] {ticker}: błąd danych")
            continue

        score = res["total_score"]
        high = entry.get("alert_high") if entry.get("alert_high") is not None else default_high
        low = entry.get("alert_low") if entry.get("alert_low") is not None else default_low

        db.save_score(ticker, score)
        db.update_watchlist_score(ticker, score, user_id)

        alert_type = None
        if score >= high and not db.was_alert_sent_today(user_id, ticker, "high_email"):
            alert_type = "high_email"
            subject = f"🟢 {ticker}: wynik wzrósł do {score:.0f}/100"
        elif score <= low and not db.was_alert_sent_today(user_id, ticker, "low_email"):
            alert_type = "low_email"
            subject = f"🔴 {ticker}: wynik spadł do {score:.0f}/100"
        else:
            continue

        body = (
            f"{res['name']} ({ticker})\n"
            f"Wynik: {score:.0f}/100\n"
            f"Cena: {res['price']} {res['currency']}\n\n"
            f"To nie jest porada inwestycyjna - sprawdź szczegóły w dashboardzie.\n"
        )
        ok, msg = send_email(
            settings["email_smtp_server"], settings["email_smtp_port"],
            settings["email_user"], settings["email_password"],
            settings["email_to"], subject, body,
        )
        if ok:
            db.mark_alert_sent(user_id, ticker, alert_type)
        log.append(f"[{user_id}] {ticker}: alert email ({score:.0f}) -> {'OK' if ok else msg}")

    return log


def send_daily_digest(user_id: str, analyze_fn) -> tuple[bool, str]:
    """
    Wysyła jeden zbiorczy e-mail z podsumowaniem CAŁEJ watchlist
    (niezależnie od progów) - przydatne jako "cotygodniowy/codzienny
    przegląd" niezależnie od alertów.
    """
    settings = db.get_email_settings(user_id)
    if not settings or not settings.get("email_to"):
        return False, "E-mail nieskonfigurowany."

    watchlist = db.get_watchlist(user_id)
    if not watchlist:
        return False, "Watchlist jest pusta - nic do wysłania."

    lines = [f"Podsumowanie watchlist ({user_id}):\n"]
    for entry in watchlist:
        ticker = entry["ticker"]
        try:
            res = analyze_fn(ticker)
        except Exception:
            lines.append(f"- {ticker}: błąd pobierania danych")
            continue
        if "error" in res:
            lines.append(f"- {ticker}: błąd danych")
            continue
        lines.append(
            f"- {ticker} ({res['name']}): {res['total_score']:.0f}/100, "
            f"cena {res['price']} {res['currency']}"
        )

    lines.append("\nTo nie jest porada inwestycyjna.")
    body = "\n".join(lines)

    return send_email(
        settings["email_smtp_server"], settings["email_smtp_port"],
        settings["email_user"], settings["email_password"],
        settings["email_to"], "📊 Codzienne podsumowanie watchlist", body,
    )
