"""
Centralne logowanie aplikacji
==============================
Konfiguruje logowanie do pliku z rotacją (logs/app.log) oraz do konsoli.
Dzięki temu mamy trwały ślad: które tickery zawiodły, kiedy złapaliśmy
rate-limit (429), ile trwał skan - przydatne zwłaszcza przy scheduler.py
działającym w tle (np. w nocy przez cron / Harmonogram zadań).

Użycie w dowolnym module:
    from app_logging import get_logger
    log = get_logger(__name__)
    log.info("Skan rozpoczęty: %d spółek", len(tickers))
    log.warning("Rate limit dla %s", ticker)
    log.exception("Nieoczekiwany błąd")   # loguje też traceback

Plik logów rotuje się automatycznie po przekroczeniu ~1 MB (max 5 kopii),
więc nie urośnie w nieskończoność.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

# Folder na logi tworzony obok pliku aplikacji.
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Flaga, żeby nie dodawać handlerów wielokrotnie (Streamlit przeładowuje moduły).
_configured = False


def _configure_root():
    """Konfiguruje root logger raz na proces (idempotentnie)."""
    global _configured
    if _configured:
        return

    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
    except Exception:
        pass  # gdyby nie dało się utworzyć folderu, zostaje samo logowanie do konsoli

    root = logging.getLogger("stockapp")
    root.setLevel(logging.INFO)
    root.propagate = False

    # Nie dubluj handlerów przy ponownym imporcie.
    if root.handlers:
        _configured = True
        return

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Handler plikowy z rotacją (1 MB, 5 kopii zapasowych).
    try:
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)
    except Exception:
        pass  # np. brak uprawnień do zapisu - trudno, lecimy dalej

    # Handler konsolowy (widoczny w terminalu, gdzie odpalono streamlit/scheduler).
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.WARNING)  # konsola tylko ostrzeżenia i błędy
    root.addHandler(console)

    _configured = True


def get_logger(name: str = "stockapp") -> logging.Logger:
    """Zwraca logger podpięty pod skonfigurowany root 'stockapp'."""
    _configure_root()
    # Wszystkie loggery pod wspólnym prefiksem dziedziczą konfigurację.
    if not name.startswith("stockapp"):
        name = f"stockapp.{name}"
    return logging.getLogger(name)


def get_log_file_path() -> str:
    return _LOG_FILE


def read_recent_logs(max_lines: int = 200) -> list[str]:
    """Zwraca ostatnie linie z pliku logów (do podglądu w UI Ustawień)."""
    try:
        with open(_LOG_FILE, encoding="utf-8") as f:
            lines = f.readlines()
        return [ln.rstrip("\n") for ln in lines[-max_lines:]]
    except FileNotFoundError:
        return []
    except Exception:
        return []
