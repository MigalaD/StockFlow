# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /alerts — alerty cenowe e-mail (Resend).

ARCHITEKTURA (dlaczego tak):
Scheduler w pamięci procesu NIE zadziała na Railway — uvicorn uruchamia
kilka workerów (każdy odpaliłby własną pętlę = zdublowane maile), a kontener
bywa usypiany. Dlatego wyzwalaczem jest ZEWNĘTRZNY cron (cron-job.org /
Railway Cron), który co 15-30 min woła POST /alerts/check z sekretem
w nagłówku. Endpoint jest bezstanowy: sprawdza progi, deduplikuje przez
alert_log (max 1 alert danego typu na ticker na dzień), wysyła i kończy.

Wysyłka: Resend (https://resend.com) — jeden klucz API, bez konfiguracji
SMTP per użytkownik. Adres odbiorcy = email z rejestracji użytkownika.

Zakres v1: progi cenowe (alert_high / alert_low) z watchlisty.
Crossover MA (pole alert_crossover) — celowo odłożone do v2.

Wymagane zmienne środowiskowe (Railway):
  RESEND_API_KEY      — klucz z panelu Resend
  ALERTS_CRON_SECRET  — losowy sekret; ten sam podajesz w cron jobie
  ALERTS_FROM         — nadawca, np. "StockFlow <alerty@stockflowx.com>"
                        (domena musi być zweryfikowana w Resend)
"""

from __future__ import annotations

import os
import sys
import logging

import requests
from fastapi import APIRouter, Header, HTTPException, status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database as db

log = logging.getLogger("stockflow.alerts")

alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

_RESEND_URL = "https://api.resend.com/emails"


def _get_price(ticker: str) -> float | None:
    """Lekkie pobranie bieżącej ceny (fast_info, fallback: ostatnie zamknięcie)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        try:
            fi = t.fast_info
            price = fi.get("lastPrice") or fi.get("last_price")
            if price and price > 0:
                return float(price)
        except Exception:
            pass
        hist = t.history(period="2d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        log.warning("Alerts: brak ceny dla %s: %s", ticker, e)
    return None


def _build_email_html(username: str, alerts: list[dict]) -> str:
    rows = "".join(
        f"<tr>"
        f"<td style='padding:8px 12px;font-family:monospace;font-weight:bold'>{a['ticker']}</td>"
        f"<td style='padding:8px 12px'>{a['message']}</td>"
        f"<td style='padding:8px 12px;font-family:monospace'>{a['price']:.2f}</td>"
        f"</tr>"
        for a in alerts
    )
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
      <h2 style="color:#16a34a">📈 StockFlow — alerty cenowe</h2>
      <p>Cześć {username}, Twoje progi cenowe zostały osiągnięte:</p>
      <table style="border-collapse:collapse;width:100%;background:#f8fafc;border-radius:8px">
        <tr style="text-align:left;border-bottom:1px solid #e2e8f0">
          <th style="padding:8px 12px">Instrument</th>
          <th style="padding:8px 12px">Alert</th>
          <th style="padding:8px 12px">Cena</th>
        </tr>
        {rows}
      </table>
      <p style="margin-top:16px">
        <a href="https://stockflowx.com/watchlist" style="color:#16a34a">Otwórz watchlistę →</a>
      </p>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
      <p style="font-size:12px;color:#64748b">
        Alerty możesz zmienić lub wyłączyć w watchliście (ikona ⚙ przy pozycji).
        Ta wiadomość ma charakter informacyjny i nie stanowi rekomendacji inwestycyjnej.
        Otrzymujesz max 1 alert danego typu na instrument dziennie.
      </p>
    </div>
    """


def _send_email(api_key: str, sender: str, to: str, subject: str, html: str) -> bool:
    try:
        resp = requests.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"from": sender, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True
        log.warning("Resend: %s %s", resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        log.warning("Resend: błąd wysyłki do %s: %s", to, e)
        return False


@alerts_router.post(
    "/check",
    summary="[CRON] Check price alerts and send emails",
    description="Wywoływane przez zewnętrzny cron z sekretem w nagłówku X-Cron-Secret.",
)
def check_alerts(x_cron_secret: str | None = Header(default=None)) -> dict:
    secret = os.getenv("ALERTS_CRON_SECRET")
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("ALERTS_FROM", "StockFlow <alerty@stockflowx.com>")

    if not secret or not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerty nieskonfigurowane: ustaw ALERTS_CRON_SECRET i RESEND_API_KEY.",
        )
    if x_cron_secret != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy sekret crona.",
        )

    users_checked = 0
    emails_sent = 0
    alerts_triggered = 0
    skipped_no_email = 0
    price_cache: dict[str, float | None] = {}   # jedna cena na ticker na przebieg

    for user_id in db.get_all_watchlist_users():
        watchlist = db.get_watchlist(user_id)
        with_alerts = [w for w in watchlist
                       if w.get("alert_high") or w.get("alert_low")]
        if not with_alerts:
            continue
        users_checked += 1

        user = db.get_user_by_username(user_id)
        email = (user or {}).get("email")

        triggered: list[dict] = []
        for w in with_alerts:
            ticker = w["ticker"]
            if ticker not in price_cache:
                price_cache[ticker] = _get_price(ticker)
            price = price_cache[ticker]
            if price is None:
                continue

            high = w.get("alert_high")
            low  = w.get("alert_low")

            if high and price >= high and not db.was_alert_sent_today(user_id, ticker, "price_high"):
                triggered.append({
                    "ticker": ticker, "price": price, "type": "price_high",
                    "message": f"Cena przekroczyła próg {high:.2f} ▲",
                })
            if low and price <= low and not db.was_alert_sent_today(user_id, ticker, "price_low"):
                triggered.append({
                    "ticker": ticker, "price": price, "type": "price_low",
                    "message": f"Cena spadła poniżej progu {low:.2f} ▼",
                })

        if not triggered:
            continue
        alerts_triggered += len(triggered)

        if not email:
            skipped_no_email += 1
            log.info("Alerts: %s ma %d alertów, ale brak emaila", user_id, len(triggered))
            continue

        subject = (f"📈 {triggered[0]['ticker']}: alert cenowy"
                   if len(triggered) == 1
                   else f"📈 StockFlow: {len(triggered)} alertów cenowych")
        html = _build_email_html(user_id, triggered)

        if _send_email(api_key, sender, email, subject, html):
            emails_sent += 1
            # Oznacz jako wysłane DOPIERO po udanej wysyłce — nieudany mail
            # zostanie ponowiony przy następnym przebiegu crona.
            for a in triggered:
                db.mark_alert_sent(user_id, a["ticker"], a["type"])

    return {
        "users_checked": users_checked,
        "alerts_triggered": alerts_triggered,
        "emails_sent": emails_sent,
        "skipped_no_email": skipped_no_email,
    }
