"""
Moduł bazy danych (SQLite)
============================
Przechowuje:
- Watchlist użytkownika (obserwowane spółki) - osobna dla każdego "użytkownika"
- Historię score liczoną dzień po dniu (przy każdym uruchomieniu skanera)
- Wyniki ostatniego skanu rynku
- Ustawienia powiadomień Telegram per użytkownik
- Log wysłanych alertów (żeby nie spamować tego samego dnia)

Plik bazy: stock_app.db (tworzy się automatycznie w tym samym folderze).

UWAGA o "użytkownikach": to NIE jest pełny system logowania z hasłami -
to prosty sposób na rozdzielenie watchlist między kilka osób korzystających
z tej samej instalacji (np. Ty i znajomy), identyfikowanych przez nazwę
wpisaną w sidebarze. Jeśli potrzebujesz prawdziwego bezpieczeństwa loginów,
dodaj np. pakiet `streamlit-authenticator`.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, date

from secrets_util import encrypt, decrypt

DB_PATH = "stock_app.db"
DEFAULT_USER = "default"


@contextmanager
def get_conn():
    # timeout=30: czekaj do 30s na zwolnienie blokady zamiast od razu rzucać
    # "database is locked" - kluczowe przy wielu użytkownikach naraz (Streamlit Cloud).
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        # WAL (Write-Ahead Logging) pozwala czytać w trakcie zapisu i znacznie
        # zmniejsza kolizje przy współbieżności. PRAGMA są tanie - ustawiamy
        # je na każde połączenie (WAL jest trwały, ale busy_timeout - nie).
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")     # 30s w ms
        conn.execute("PRAGMA synchronous=NORMAL")     # bezpieczny kompromis przy WAL
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        # --- watchlist (z migracją dla starszych wersji bazy) ---
        existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()}

        if not existing_cols:
            # brak tabeli - tworzymy od razu w nowym formacie
            conn.execute("""
                CREATE TABLE watchlist (
                    user_id TEXT NOT NULL DEFAULT 'default',
                    ticker TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    last_score REAL,
                    last_checked TEXT,
                    alert_high REAL,
                    alert_low REAL,
                    PRIMARY KEY (user_id, ticker)
                )
            """)
        elif "user_id" not in existing_cols:
            # stara tabela ze starym PRIMARY KEY (ticker) - trzeba przebudować,
            # bo inaczej dwóch użytkowników nie mogłoby obserwować tej samej spółki
            conn.execute("ALTER TABLE watchlist RENAME TO watchlist_old")
            conn.execute("""
                CREATE TABLE watchlist (
                    user_id TEXT NOT NULL DEFAULT 'default',
                    ticker TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    last_score REAL,
                    last_checked TEXT,
                    alert_high REAL,
                    alert_low REAL,
                    PRIMARY KEY (user_id, ticker)
                )
            """)
            conn.execute("""
                INSERT INTO watchlist (user_id, ticker, added_at, last_score, last_checked)
                SELECT 'default', ticker, added_at, last_score, last_checked FROM watchlist_old
            """)
            conn.execute("DROP TABLE watchlist_old")
        else:
            # tabela już w nowym formacie - dodaj brakujące kolumny, jeśli trzeba
            if "alert_high" not in existing_cols:
                conn.execute("ALTER TABLE watchlist ADD COLUMN alert_high REAL")
            if "alert_low" not in existing_cols:
                conn.execute("ALTER TABLE watchlist ADD COLUMN alert_low REAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                score REAL NOT NULL,
                PRIMARY KEY (ticker, date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_results (
                ticker TEXT NOT NULL,
                name TEXT,
                sector TEXT,
                price REAL,
                score REAL,
                scanned_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                telegram_token TEXT,
                telegram_chat_id TEXT
            )
        """)
        settings_cols = {r["name"] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()}
        for col in ("email_to", "email_smtp_server", "email_smtp_port", "email_user", "email_password"):
            if col not in settings_cols:
                col_type = "INTEGER" if col == "email_smtp_port" else "TEXT"
                conn.execute(f"ALTER TABLE user_settings ADD COLUMN {col} {col_type}")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                user_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker, date, alert_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                buy_price REAL NOT NULL,
                buy_date TEXT NOT NULL,
                notes TEXT,
                added_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT NOT NULL,
                period TEXT NOT NULL,
                data TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                PRIMARY KEY (ticker, period)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                ticker TEXT,
                decision TEXT NOT NULL,
                reason TEXT,
                score_at_entry REAL,
                price_at_entry REAL,
                created_at TEXT NOT NULL
            )
        """)

    # Po utworzeniu tabel bazowych uruchom migracje schematu.
    run_migrations()


# ----------------------------------------------------------------------
# SYSTEM MIGRACJI SCHEMATU
# ----------------------------------------------------------------------
# Zamiast ręcznie sprawdzać kolumny w init_db przy każdej zmianie, każda
# zmiana schematu to ponumerowana migracja. Tabela schema_version pamięta,
# która migracja została już zastosowana, więc istniejące bazy są
# bezpiecznie aktualizowane bez utraty danych.
#
# Aby dodać nową zmianę schematu: dopisz funkcję _migration_N(conn) i wpis
# w MIGRATIONS. NIGDY nie zmieniaj istniejących migracji - tylko dodawaj nowe.
# ----------------------------------------------------------------------
def _get_schema_version(conn) -> int:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
    """)
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return (row["v"] if row and row["v"] is not None else 0)


def _set_schema_version(conn, version: int):
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def _column_exists(conn, table: str, column: str) -> bool:
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    return column in cols


def _migration_1(conn):
    """Dodaje kolumny do alertów crossover MA (złoty/krzyż śmierci) w watchlist."""
    if not _column_exists(conn, "watchlist", "alert_crossover"):
        conn.execute("ALTER TABLE watchlist ADD COLUMN alert_crossover INTEGER DEFAULT 0")
    # pamięć ostatnio wykrytego stanu trendu (MA50 vs MA200), żeby wykrywać
    # dopiero ZMIANĘ (przecięcie), a nie sam fakt że MA50 > MA200.
    if not _column_exists(conn, "watchlist", "last_ma_state"):
        conn.execute("ALTER TABLE watchlist ADD COLUMN last_ma_state TEXT")


# Lista migracji: (numer_wersji, funkcja). Stosowane rosnąco.
MIGRATIONS = [
    (1, _migration_1),
]


def run_migrations():
    """Stosuje wszystkie migracje nowsze niż aktualna wersja schematu."""
    with get_conn() as conn:
        current = _get_schema_version(conn)
        for version, migration in MIGRATIONS:
            if version > current:
                migration(conn)
                _set_schema_version(conn, version)


# ----------------------------------------------------------------------
# WATCHLIST
# ----------------------------------------------------------------------
def add_to_watchlist(ticker: str, user_id: str = DEFAULT_USER):
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
            (user_id, ticker, datetime.now().isoformat()),
        )


def remove_from_watchlist(ticker: str, user_id: str = DEFAULT_USER):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE ticker = ? AND user_id = ?",
            (ticker.upper(), user_id),
        )


def get_watchlist(user_id: str = DEFAULT_USER) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_watchlist_users() -> list[str]:
    """Lista wszystkich user_id, którzy mają coś w watchlist - używane przez scheduler."""
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT user_id FROM watchlist").fetchall()
        return [r["user_id"] for r in rows]


def update_watchlist_score(ticker: str, score: float, user_id: str = DEFAULT_USER):
    with get_conn() as conn:
        conn.execute(
            "UPDATE watchlist SET last_score = ?, last_checked = ? "
            "WHERE ticker = ? AND user_id = ?",
            (score, datetime.now().isoformat(), ticker.upper(), user_id),
        )


def set_watchlist_alerts(ticker: str, alert_high: float | None, alert_low: float | None,
                          user_id: str = DEFAULT_USER):
    """Ustawia własne progi alertów dla spółki (None = brak alertu danego typu)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE watchlist SET alert_high = ?, alert_low = ? "
            "WHERE ticker = ? AND user_id = ?",
            (alert_high, alert_low, ticker.upper(), user_id),
        )


def set_crossover_alert(ticker: str, enabled: bool, user_id: str = DEFAULT_USER):
    """Włącza/wyłącza alert o przecięciu MA50/MA200 (złoty/krzyż śmierci)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE watchlist SET alert_crossover = ? WHERE ticker = ? AND user_id = ?",
            (1 if enabled else 0, ticker.upper(), user_id),
        )


def update_ma_state(ticker: str, ma_state: str, user_id: str = DEFAULT_USER):
    """Zapisuje ostatni znany stan trendu MA ('golden' lub 'death').

    Używane, by wykrywać dopiero ZMIANĘ stanu (przecięcie), a nie sam fakt
    że MA50 jest powyżej/poniżej MA200.
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE watchlist SET last_ma_state = ? WHERE ticker = ? AND user_id = ?",
            (ma_state, ticker.upper(), user_id),
        )


# ----------------------------------------------------------------------
# SCORE HISTORY
# ----------------------------------------------------------------------
def save_score(ticker: str, score: float, day: str | None = None):
    day = day or date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO score_history (ticker, date, score) VALUES (?, ?, ?)",
            (ticker.upper(), day, score),
        )


def get_score_history(ticker: str, limit_days: int = 365) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, score FROM score_history WHERE ticker = ? "
            "ORDER BY date DESC LIMIT ?",
            (ticker.upper(), limit_days),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_previous_score(ticker: str) -> float | None:
    """Score z dnia poprzedniego dostępnego pomiaru (do porównań dzień-do-dnia)."""
    history = get_score_history(ticker, limit_days=2)
    if len(history) >= 2:
        return history[-2]["score"]
    return None


# ----------------------------------------------------------------------
# SCAN RESULTS
# ----------------------------------------------------------------------
def save_scan_results(results: list[dict]):
    """results: list of dicts with keys ticker, name, sector, price, score"""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("DELETE FROM scan_results")  # keep only latest scan
        conn.executemany(
            "INSERT INTO scan_results (ticker, name, sector, price, score, scanned_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(r["ticker"], r.get("name"), r.get("sector"), r.get("price"), r["score"], now)
             for r in results],
        )


def get_scan_results() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scan_results ORDER BY score DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_last_scan_time() -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(scanned_at) as t FROM scan_results").fetchone()
        return row["t"] if row and row["t"] else None


# ----------------------------------------------------------------------
# USER SETTINGS (Telegram)
# ----------------------------------------------------------------------
def save_telegram_settings(user_id: str, token: str, chat_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_settings (user_id, telegram_token, telegram_chat_id) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "telegram_token = excluded.telegram_token, "
            "telegram_chat_id = excluded.telegram_chat_id",
            (user_id, encrypt(token), chat_id),
        )


def get_telegram_settings(user_id: str = DEFAULT_USER) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT telegram_token, telegram_chat_id FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["telegram_token"] = decrypt(d.get("telegram_token"))
        return d


def get_all_telegram_users() -> list[dict]:
    """Wszyscy użytkownicy z skonfigurowanym Telegramem - używane przez scheduler."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, telegram_token, telegram_chat_id FROM user_settings "
            "WHERE telegram_token IS NOT NULL AND telegram_chat_id IS NOT NULL "
            "AND telegram_token != '' AND telegram_chat_id != ''"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["telegram_token"] = decrypt(d.get("telegram_token"))
            out.append(d)
        return out


# ----------------------------------------------------------------------
# USER SETTINGS (Email)
# ----------------------------------------------------------------------
def save_email_settings(user_id: str, smtp_server: str, smtp_port: int,
                         email_user: str, email_password: str, email_to: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_settings (user_id, email_smtp_server, email_smtp_port, "
            "email_user, email_password, email_to) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "email_smtp_server = excluded.email_smtp_server, "
            "email_smtp_port = excluded.email_smtp_port, "
            "email_user = excluded.email_user, "
            "email_password = excluded.email_password, "
            "email_to = excluded.email_to",
            (user_id, smtp_server, smtp_port, email_user, encrypt(email_password), email_to),
        )


def get_email_settings(user_id: str = DEFAULT_USER) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT email_smtp_server, email_smtp_port, email_user, "
            "email_password, email_to FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["email_password"] = decrypt(d.get("email_password"))
        return d


def get_all_email_users() -> list[dict]:
    """Wszyscy użytkownicy z skonfigurowanym e-mailem - używane przez scheduler."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, email_smtp_server, email_smtp_port, email_user, "
            "email_password, email_to FROM user_settings "
            "WHERE email_to IS NOT NULL AND email_smtp_server IS NOT NULL "
            "AND email_to != '' AND email_smtp_server != ''"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["email_password"] = decrypt(d.get("email_password"))
            out.append(d)
        return out


# ----------------------------------------------------------------------
# PORTFOLIO
# ----------------------------------------------------------------------
def add_position(user_id: str, ticker: str, shares: float, buy_price: float,
                  buy_date: str, notes: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio (user_id, ticker, shares, buy_price, buy_date, notes, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, ticker.upper().strip(), shares, buy_price, buy_date, notes,
             datetime.now().isoformat()),
        )


def remove_position(position_id: int, user_id: str = DEFAULT_USER):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM portfolio WHERE id = ? AND user_id = ?",
            (position_id, user_id),
        )


def get_portfolio(user_id: str = DEFAULT_USER) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM portfolio WHERE user_id = ? ORDER BY buy_date DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# ALERT LOG (żeby nie wysyłać tego samego alertu wiele razy dziennie)
# ----------------------------------------------------------------------
def was_alert_sent_today(user_id: str, ticker: str, alert_type: str) -> bool:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM alert_log WHERE user_id=? AND ticker=? AND date=? AND alert_type=?",
            (user_id, ticker.upper(), today, alert_type),
        ).fetchone()
        return row is not None


def mark_alert_sent(user_id: str, ticker: str, alert_type: str):
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO alert_log (user_id, ticker, date, alert_type) "
            "VALUES (?, ?, ?, ?)",
            (user_id, ticker.upper(), today, alert_type),
        )


# ----------------------------------------------------------------------
# LOKALNY CACHE CEN (współdzielony między userami i sesjami)
# ----------------------------------------------------------------------
def get_price_cache(ticker: str, period: str, max_age_seconds: int = 900) -> str | None:
    """
    Zwraca zapisany JSON z danymi cenowymi, jeśli istnieje i nie jest
    starszy niż `max_age_seconds`. W przeciwnym razie None.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT data, cached_at FROM price_cache WHERE ticker = ? AND period = ?",
            (ticker.upper(), period),
        ).fetchone()
        if not row:
            return None
        cached_at = datetime.fromisoformat(row["cached_at"])
        age = (datetime.now() - cached_at).total_seconds()
        if age > max_age_seconds:
            return None
        return row["data"]


def set_price_cache(ticker: str, period: str, data_json: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO price_cache (ticker, period, data, cached_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ticker, period) DO UPDATE SET data = excluded.data, "
            "cached_at = excluded.cached_at",
            (ticker.upper(), period, data_json, datetime.now().isoformat()),
        )


def clear_price_cache():
    """Usuwa wszystkie wpisy z cache cen - przydatne przy problemach z danymi."""
    with get_conn() as conn:
        conn.execute("DELETE FROM price_cache")


def get_price_cache_stats() -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as n, MIN(cached_at) as oldest, MAX(cached_at) as newest "
            "FROM price_cache"
        ).fetchone()
        return dict(row)


# ----------------------------------------------------------------------
# DZIENNIK INWESTYCYJNY
# ----------------------------------------------------------------------
def add_journal_entry(user_id: str, entry_date: str, ticker: str, decision: str,
                       reason: str = "", score_at_entry: float | None = None,
                       price_at_entry: float | None = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO journal (user_id, entry_date, ticker, decision, reason, "
            "score_at_entry, price_at_entry, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, entry_date, ticker.upper().strip() if ticker else None,
             decision, reason, score_at_entry, price_at_entry,
             datetime.now().isoformat()),
        )


def get_journal_entries(user_id: str = DEFAULT_USER, ticker: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM journal WHERE user_id = ? AND ticker = ? "
                "ORDER BY entry_date DESC, id DESC",
                (user_id, ticker.upper()),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM journal WHERE user_id = ? ORDER BY entry_date DESC, id DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def delete_journal_entry(entry_id: int, user_id: str = DEFAULT_USER):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM journal WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )


init_db()
