# Copyright (c) 2026 Damian Migała / StockFlow (Analizator Spółek)
# Wszystkie prawa zastrzeżone. All rights reserved.
# Zobacz plik LICENSE w katalogu głównym repozytorium.

"""
Powiadomienia Telegram
========================
Wysyła alerty na Telegram, gdy spółka z watchlist przekroczy ustawiony
przez użytkownika próg wyniku (score).

Jak skonfigurować (instrukcja również w dashboardzie, zakładka "Ustawienia"):
1. W Telegramie znajdź bota @BotFather, wpisz /newbot i postępuj według
   instrukcji - otrzymasz TOKEN bota.
2. Napisz CZYMKOLWIEK do swojego nowego bota (musi mieć z Tobą rozpoczętą
   rozmowę, żeby mógł Ci pisać).
3. Wejdź na: https://api.telegram.org/bot<TOKEN>/getUpdates
   i znajdź swoje "chat":{"id": ...} - to Twój CHAT_ID.
4. Wpisz TOKEN i CHAT_ID w zakładce "Ustawienia" dashboardu.

Ten moduł jest używany przez:
- dashboard.py (przycisk "Wyślij testowe powiadomienie")
- scheduler.py (automatyczne sprawdzanie watchlist i wysyłanie alertów)
"""

from __future__ import annotations

import urllib.request
import urllib.parse
import json

import database as db


def send_telegram_message(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    """
    Wysyła wiadomość przez Telegram Bot API.
    Zwraca (sukces, komunikat_błędu_lub_OK).
    """
    if not token or not chat_id:
        return False, "Brak tokena lub chat_id."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return True, "OK"
            return False, body.get("description", "Nieznany błąd Telegrama")
    except Exception as e:
        return False, str(e)


def default_thresholds() -> tuple[float, float]:
    """Domyślne progi alertów, jeśli użytkownik nie ustawił własnych dla spółki."""
    return 70.0, 30.0  # alert_high, alert_low


def check_and_send_alerts(user_id: str, analyze_fn) -> list[str]:
    """
    Sprawdza watchlist danego użytkownika i wysyła alerty Telegram, gdy:
    - score spółki >= alert_high (lub domyślnie 70) i alert nie był wysłany dziś
    - score spółki <= alert_low (lub domyślnie 30) i alert nie był wysłany dziś

    analyze_fn: funkcja(ticker) -> wynik analizy (np. stock_analyzer.analyze_ticker)

    Zwraca listę komunikatów (do logowania / wyświetlenia).
    """
    log = []
    settings = db.get_telegram_settings(user_id)
    if not settings or not settings.get("telegram_token") or not settings.get("telegram_chat_id"):
        return [f"[{user_id}] Telegram nieskonfigurowany - pomijam."]

    token = settings["telegram_token"]
    chat_id = settings["telegram_chat_id"]

    watchlist = db.get_watchlist(user_id)
    default_high, default_low = default_thresholds()

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

        if score >= high and not db.was_alert_sent_today(user_id, ticker, "high"):
            text = (
                f"🟢 *{ticker}* ({res['name']})\n"
                f"Wynik wzrósł do *{score:.0f}/100* (próg: {high:.0f})\n"
                f"Cena: {res['price']} {res['currency']}\n\n"
                f"_To nie jest porada inwestycyjna - sprawdź szczegóły w dashboardzie._"
            )
            ok, msg = send_telegram_message(token, chat_id, text)
            if ok:
                db.mark_alert_sent(user_id, ticker, "high")
            log.append(f"[{user_id}] {ticker}: alert HIGH ({score:.0f}) -> {'OK' if ok else msg}")

        elif score <= low and not db.was_alert_sent_today(user_id, ticker, "low"):
            text = (
                f"🔴 *{ticker}* ({res['name']})\n"
                f"Wynik spadł do *{score:.0f}/100* (próg: {low:.0f})\n"
                f"Cena: {res['price']} {res['currency']}\n\n"
                f"_To nie jest porada inwestycyjna - sprawdź szczegóły w dashboardzie._"
            )
            ok, msg = send_telegram_message(token, chat_id, text)
            if ok:
                db.mark_alert_sent(user_id, ticker, "low")
            log.append(f"[{user_id}] {ticker}: alert LOW ({score:.0f}) -> {'OK' if ok else msg}")

        # Alert o przecięciu MA50/MA200 (złoty krzyż / krzyż śmierci).
        if entry.get("alert_crossover"):
            crossover = res.get("ma_crossover")
            if crossover and crossover.get("crossed"):
                kind = crossover["type"]  # 'golden' albo 'death'
                prev_state = entry.get("last_ma_state")
                # wyślij tylko jeśli faktycznie zmienił się stan względem zapisanego
                if prev_state != kind and not db.was_alert_sent_today(user_id, ticker, f"cross_{kind}"):
                    if kind == "golden":
                        text = (
                            f"⭐ *{ticker}* ({res['name']})\n"
                            f"*Złoty krzyż* - MA50 przecięła MA200 od dołu (sygnał byczy)\n"
                            f"Cena: {res['price']} {res['currency']}\n\n"
                            f"_To nie jest porada inwestycyjna._"
                        )
                    else:
                        text = (
                            f"💀 *{ticker}* ({res['name']})\n"
                            f"*Krzyż śmierci* - MA50 spadła poniżej MA200 (sygnał niedźwiedzi)\n"
                            f"Cena: {res['price']} {res['currency']}\n\n"
                            f"_To nie jest porada inwestycyjna._"
                        )
                    ok, msg = send_telegram_message(token, chat_id, text)
                    if ok:
                        db.mark_alert_sent(user_id, ticker, f"cross_{kind}")
                    log.append(f"[{user_id}] {ticker}: alert CROSSOVER ({kind}) -> {'OK' if ok else msg}")
            # zapamiętaj aktualny stan trendu na potrzeby kolejnego sprawdzenia
            if crossover:
                db.update_ma_state(ticker, crossover["state"], user_id)

    return log
