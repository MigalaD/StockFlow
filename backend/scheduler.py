#!/usr/bin/env python3
# Copyright (c) 2026 Damian Migała / StockFlow

"""
StockFlow Alert Scheduler
=========================
Sprawdza wyniki score dla wszystkich watchlist i wysyła alerty
gdy score przekracza progi ustawione przez użytkownika.

Uruchamianie:
  python -m backend.scheduler          # jednorazowo
  python -m backend.scheduler --loop   # co N minut

Jako Railway Cron Job (zalecane):
  Ustaw w railway.toml:
  [cron]
  schedule = "*/30 * * * *"   # co 30 minut
  command  = "python -m backend.scheduler"

Zmienne środowiskowe:
  SCHEDULER_INTERVAL_MINUTES  — interwał pętli (domyślnie 30)
  Reszta ze standardowego .env (DATABASE_URL, itp.)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db
from stock_analyzer import analyze_ticker

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [SCHEDULER] %(levelname)s %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "30"))


# ── Kanały powiadomień ────────────────────────────────────────────────

def send_telegram(token: str, chat_id: str, message: str) -> bool:
    """Wysyła wiadomość przez Telegram Bot API."""
    try:
        import requests
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id":    chat_id,
            "text":       message,
            "parse_mode": "Markdown",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        log.warning(f"Telegram error: {e}")
        return False


def send_email(settings: dict, subject: str, body: str) -> bool:
    """Wysyła email przez SMTP."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg           = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"]    = settings.get("email_user", "")
        msg["To"]      = settings.get("email_to", "")

        server = smtplib.SMTP(
            settings.get("email_smtp_server", "smtp.gmail.com"),
            int(settings.get("email_smtp_port", 587)),
        )
        server.starttls()
        server.login(settings["email_user"], settings["email_password"])
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        log.warning(f"Email error: {e}")
        return False


def format_alert_message(
    ticker:     str,
    score:      float,
    alert_type: str,
    threshold:  float,
    user_id:    str,
) -> str:
    emoji = "🟢" if score >= 60 else "🟡" if score >= 40 else "🔴"
    return (
        f"📊 *StockFlow Alert* — {ticker}\n\n"
        f"{emoji} Score DT: *{score:.0f}/100*\n"
        f"🔔 Próg {alert_type}: {threshold:.0f}\n\n"
        f"Sprawdź szczegóły w aplikacji StockFlow."
    )


# ── Główna logika ─────────────────────────────────────────────────────

def check_alerts_for_user(user_id: str) -> int:
    """
    Sprawdza alerty dla jednego użytkownika.
    Zwraca liczbę wysłanych powiadomień.
    """
    watchlist = db.get_watchlist(user_id)
    if not watchlist:
        return 0

    settings = db.get_user_settings(user_id) or {}
    today    = str(date.today())
    sent     = 0

    for entry in watchlist:
        ticker      = entry["ticker"]
        alert_high  = entry.get("alert_high")
        alert_low   = entry.get("alert_low")
        crossover   = bool(entry.get("alert_crossover", False))

        # Analiza tickera
        try:
            result = analyze_ticker(ticker)
        except Exception as e:
            log.warning(f"  {ticker}: analiza nieudana — {e}")
            continue

        if "error" in result:
            continue

        score = result["total_score"]

        # Zapisz zaktualizowany score
        db.update_watchlist_score(ticker, score, user_id)

        # ── Sprawdź alerty ──────────────────────────────────────────
        alerts_to_send: list[tuple[str, float]] = []

        if alert_high and score >= alert_high:
            alert_key = f"high_{alert_high}"
            if not db.alert_already_sent(user_id, ticker, today, alert_key):
                alerts_to_send.append(("wysoki", alert_high))
                db.mark_alert_sent(user_id, ticker, today, alert_key)

        if alert_low and score <= alert_low:
            alert_key = f"low_{alert_low}"
            if not db.alert_already_sent(user_id, ticker, today, alert_key):
                alerts_to_send.append(("niski", alert_low))
                db.mark_alert_sent(user_id, ticker, today, alert_key)

        if crossover and result.get("ma_crossover"):
            crossover_type = result["ma_crossover"].get("type", "")
            if crossover_type:
                alert_key = f"crossover_{crossover_type}_{today}"
                if not db.alert_already_sent(user_id, ticker, today, alert_key):
                    alerts_to_send.append((f"crossover {crossover_type}", score))
                    db.mark_alert_sent(user_id, ticker, today, alert_key)

        # ── Wyślij powiadomienia ────────────────────────────────────
        for alert_type, threshold in alerts_to_send:
            message = format_alert_message(ticker, score, alert_type, threshold, user_id)
            log.info(f"  ALERT: {user_id}/{ticker} — {alert_type} (score={score:.0f})")

            tg_token  = settings.get("telegram_token")
            tg_chatid = settings.get("telegram_chat_id")
            if tg_token and tg_chatid:
                ok = send_telegram(tg_token, tg_chatid, message)
                log.info(f"    Telegram: {'✓ wysłano' if ok else '✗ błąd'}")
                if ok:
                    sent += 1

            if settings.get("email_user") and settings.get("email_to"):
                ok = send_email(
                    settings,
                    subject=f"StockFlow Alert: {ticker} (score={score:.0f})",
                    body=message.replace("*", ""),
                )
                log.info(f"    Email: {'✓ wysłano' if ok else '✗ błąd'}")
                if ok:
                    sent += 1

    return sent


def run_once() -> None:
    """Jednorazowe sprawdzenie alertów dla wszystkich użytkowników."""
    log.info("=== StockFlow Scheduler — start ===")
    start = time.time()

    users = db.get_all_users_with_watchlist()
    log.info(f"Użytkownicy z watchlistą: {len(users)}")

    total_sent = 0
    for user_id in users:
        log.info(f"Sprawdzam: {user_id}")
        try:
            sent = check_alerts_for_user(user_id)
            total_sent += sent
        except Exception as e:
            log.error(f"  Błąd dla {user_id}: {e}")

    elapsed = time.time() - start
    log.info(f"=== Zakończono w {elapsed:.1f}s · {total_sent} alertów wysłanych ===")


def run_loop(interval_minutes: int) -> None:
    """Pętla nieskończona — sprawdza alerty co N minut."""
    log.info(f"Tryb pętli: co {interval_minutes} minut")
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Błąd głównej pętli: {e}")
        log.info(f"Czekam {interval_minutes} min…")
        time.sleep(interval_minutes * 60)


# ── Pomocnicze funkcje bazy danych ───────────────────────────────────

def _patch_database() -> None:
    """
    Dodaje funkcje do database.py których scheduler potrzebuje
    a które mogą nie być jeszcze zdefiniowane.
    """
    # alert_already_sent / mark_alert_sent
    if not hasattr(db, "alert_already_sent"):
        def alert_already_sent(user_id: str, ticker: str, date_: str, alert_type: str) -> bool:
            with db.get_conn() as conn:
                row = conn.execute(
                    "SELECT 1 FROM alert_log WHERE user_id=? AND ticker=? AND date=? AND alert_type=?",
                    (user_id, ticker, date_, alert_type),
                ).fetchone()
                return row is not None

        def mark_alert_sent(user_id: str, ticker: str, date_: str, alert_type: str) -> None:
            with db.get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO alert_log (user_id, ticker, date, alert_type) VALUES (?,?,?,?)",
                    (user_id, ticker, date_, alert_type),
                )

        def get_all_users_with_watchlist() -> list[str]:
            with db.get_conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT user_id FROM watchlist"
                ).fetchall()
                return [r["user_id"] for r in rows]

        db.alert_already_sent        = alert_already_sent
        db.mark_alert_sent           = mark_alert_sent
        db.get_all_users_with_watchlist = get_all_users_with_watchlist


if __name__ == "__main__":
    _patch_database()

    parser = argparse.ArgumentParser(description="StockFlow Alert Scheduler")
    parser.add_argument("--loop", action="store_true", help="Tryb pętli (zamiast jednorazowego)")
    parser.add_argument("--interval", type=int, default=INTERVAL_MINUTES, help="Interwał w minutach")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.interval)
    else:
        run_once()
