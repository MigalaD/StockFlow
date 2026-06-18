"""
Skaner Rynku
=============
Przelicza score dla listy spółek i zapisuje wyniki do bazy SQLite.

Uruchamianie:
    python scanner.py [usa|gpw|europa|krypto|all]
"""

from __future__ import annotations

import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from stock_analyzer import analyze_ticker
from tickers import (
    SKANER_USA, SKANER_GPW, SKANER_EUROPA, SKANER_WSZYSTKIE,
    SKANER_KRYPTO,
)
import database as db
from app_logging import get_logger

log = get_logger("scanner")

# Maksymalna liczba równoległych żądań do Yahoo Finance.
# Więcej = szybciej, ale większe ryzyko rate-limitu.
# 8 to dobry kompromis (I/O-bound, czekamy na sieć).
# Maksymalna liczba równoległych wątków. Faktyczne tempo zapytań do Yahoo
# Finance i tak ogranicza globalny token bucket (rate_limiter.py, ~8 req/s),
# więc nawet przy większej liczbie wątków nie przekroczymy bezpiecznego limitu.
MAX_WORKERS = 8


def _analyze_one(ticker: str) -> dict | None:
    """Analizuje jeden ticker; zwraca dict lub None przy błędzie."""
    try:
        res = analyze_ticker(ticker)
        if "error" in res:
            return None
        return {
            "ticker": res["ticker"],
            "name":   res["name"],
            "sector": res.get("sector", "Nieznany"),
            "price":  res["price"],
            "score":  res["total_score"],
        }
    except Exception as e:
        log.warning("Błąd analizy %s: %s", ticker, e)
        return None


def scan_market(
    tickers: list[str],
    progress_callback=None,
    max_workers: int = MAX_WORKERS,
) -> list[dict]:
    """
    Równoległe skanowanie listy tickerów (ThreadPoolExecutor).

    progress_callback(done, total, ticker) – opcjonalna funkcja do
    raportowania postępu (np. pasek postępu Streamlit).

    Zwraca posortowaną listę {ticker, name, sector, price, score}
    i zapisuje wyniki do bazy.
    """
    results = []
    total = len(tickers)
    done_count = 0
    failed = 0
    lock = threading.Lock()

    log.info("Skan rozpoczęty: %d instrumentów, max %d wątków", total, max_workers)
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(_analyze_one, t): t for t in tickers}

        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            entry = future.result()

            with lock:
                done_count += 1
                dc = done_count
                if not entry:
                    failed += 1

            if entry:
                results.append(entry)
                db.save_score(entry["ticker"], entry["score"])

            if progress_callback:
                progress_callback(dc, total, ticker)

    results.sort(key=lambda r: -r["score"])
    db.save_scan_results(results)

    elapsed = time.time() - t_start
    log.info("Skan zakończony w %.1fs: %d OK, %d błędów",
             elapsed, len(results), failed)
    return results


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    if arg == "usa":
        tickers = SKANER_USA
    elif arg == "gpw":
        tickers = SKANER_GPW
    elif arg == "europa":
        tickers = SKANER_EUROPA
    elif arg == "krypto":
        tickers = SKANER_KRYPTO
    else:
        tickers = SKANER_WSZYSTKIE

    print(f"Równoległe skanowanie {len(tickers)} instrumentów "
          f"(max {MAX_WORKERS} wątków)...")

    t0 = time.time()

    def progress(done, total, ticker):
        print(f"  [{done}/{total}] {ticker}")

    results = scan_market(tickers, progress_callback=progress)

    elapsed = time.time() - t0
    print(f"\nZakończono w {elapsed:.1f}s. "
          f"Zapisano {len(results)} wyników do bazy.")
    print("\nTOP 5:")
    for r in results[:5]:
        print(f"  {r['ticker']:12s} {r['score']:6.1f}  {r['name']}")
    print("\nBOTTOM 5:")
    for r in results[-5:]:
        print(f"  {r['ticker']:12s} {r['score']:6.1f}  {r['name']}")


if __name__ == "__main__":
    main()
