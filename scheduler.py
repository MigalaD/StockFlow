"""
Scheduler - codzienne zadanie
================================
Skrypt do uruchamiania RAZ DZIENNIE (np. przez Windows Task Scheduler
albo cron na Linux/Mac). Robi dwie rzeczy:

1. Skanuje rynek (jak scanner.py) i zapisuje wyniki do bazy - dzięki temu
   historia score (zakładka "Historia sygnału", watchlist) jest oparta
   na realnych danych dzień-po-dniu, nie tylko na "od ostatniej wizyty".

2. Sprawdza watchlist każdego użytkownika i wysyła powiadomienia Telegram,
   jeśli score przekroczył ustawione progi.

Użycie:
    python scheduler.py            -> skanuje SKANER_WSZYSTKIE + alerty
    python scheduler.py usa        -> skanuje SKANER_USA + alerty
    python scheduler.py gpw        -> skanuje SKANER_GPW + alerty
    python scheduler.py --no-scan  -> pomija skan, tylko alerty z watchlist

------------------------------------------------------------------------
JAK USTAWIĆ AUTOMATYCZNE URUCHAMIANIE:

Windows (Task Scheduler):
  1. Otwórz "Harmonogram zadań" (Task Scheduler)
  2. Utwórz nowe zadanie -> Wyzwalacz: codziennie, np. 18:00
  3. Akcja: Uruchom program
     - Program: ścieżka do python.exe w Twoim .venv
       (np. C:\\Users\\...\\StockApp\\.venv\\Scripts\\python.exe)
     - Argumenty: scheduler.py
     - Katalog startowy: folder z plikami tej aplikacji

Linux/Mac (cron):
  1. crontab -e
  2. Dodaj linię (przykład: codziennie 18:00):
     0 18 * * * cd /sciezka/do/StockApp && /sciezka/do/.venv/bin/python scheduler.py
------------------------------------------------------------------------
"""

from __future__ import annotations

import sys
from datetime import datetime

from stock_analyzer import analyze_ticker
from tickers import SKANER_USA, SKANER_GPW, SKANER_EUROPA, SKANER_WSZYSTKIE
from scanner import scan_market
from telegram_alerts import check_and_send_alerts
import database as db


def run_scan(arg: str):
    if arg == "usa":
        tickers = SKANER_USA
    elif arg == "gpw":
        tickers = SKANER_GPW
    elif arg == "europa":
        tickers = SKANER_EUROPA
    else:
        tickers = SKANER_WSZYSTKIE

    print(f"[{datetime.now().isoformat(timespec='seconds')}] Skanowanie {len(tickers)} spolek...")

    def progress(done, total, ticker):
        if done % 10 == 0 or done == total:
            print(f"  {done}/{total}...")

    results = scan_market(tickers, progress_callback=progress)
    print(f"  Zakonczono. Zapisano {len(results)} wynikow.")


def run_alerts():
    print(f"[{datetime.now().isoformat(timespec='seconds')}] Sprawdzanie watchlist i alertow...")

    users = set(db.get_all_watchlist_users())
    telegram_users = {u["user_id"] for u in db.get_all_telegram_users()}
    relevant_users = users | telegram_users

    if not relevant_users:
        print("  Brak uzytkownikow z watchlist / ustawieniami Telegram.")
        return

    for user_id in relevant_users:
        log = check_and_send_alerts(user_id, analyze_ticker)
        for line in log:
            print(f"  {line}")


def main():
    args = sys.argv[1:]
    no_scan = "--no-scan" in args
    args = [a for a in args if a != "--no-scan"]
    arg = args[0].lower() if args else "all"

    if not no_scan:
        run_scan(arg)
    else:
        print("Pomijam skan (--no-scan).")

    run_alerts()
    print("Zakonczono.")


if __name__ == "__main__":
    main()
