# Copyright (c) 2026 Damian Migała / StockFlow

"""
Warstwa abstrakcji bazy danych — SQLite (dev) lub PostgreSQL/Supabase (produkcja).

Przełączanie przez zmienną środowiskową DATABASE_URL:
  - Brak DATABASE_URL  → SQLite (istniejący database.py Streamlit)
  - DATABASE_URL ustawiony → PostgreSQL przez asyncpg (Supabase)

Wzorzec użycia w routerach FastAPI:
    from backend.core.database import get_db, Database

    @router.get("/...")
    async def endpoint(db: Database = Depends(get_db)):
        result = await db.fetchall("SELECT * FROM watchlist WHERE user_id = $1", user_id)

Kompatybilność SQL:
  SQLite używa ? jako placeholder, PostgreSQL używa $1, $2, ...
  Ta warstwa normalizuje to automatycznie przez _adapt_query().
"""

from __future__ import annotations

import os
import re
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from .config import get_settings

settings = get_settings()


def _adapt_query(sql: str, use_postgres: bool) -> str:
    """
    Konwertuje placeholdery SQL między dialektami.

    SQLite używa ?, PostgreSQL używa $1, $2...
    Funkcja jest idempotentna: jeśli query już zawiera $N — nie zmienia.

    Przykład:
        "SELECT * FROM t WHERE id = ? AND name = ?"
        → "SELECT * FROM t WHERE id = $1 AND name = $2"
    """
    if not use_postgres:
        # SQLite: zamień $N → ? (na wypadek gdyby ktoś napisał w stylu postgres)
        return re.sub(r'\$\d+', '?', sql)

    # PostgreSQL: zamień ? → $1, $2, ...
    counter = 0
    def replace(m):
        nonlocal counter
        counter += 1
        return f"${counter}"
    return re.sub(r'\?', replace, sql)


# ── SQLite adapter (synchroniczny, działa z istniejącym database.py) ──

class _SQLiteDB:
    """Synchroniczny adapter SQLite owinięty w async interface."""

    def __init__(self):
        import database as _db
        self._db = _db

    async def fetchall(self, sql: str, *params) -> list[dict]:
        sql = _adapt_query(sql, use_postgres=False)
        with self._db.get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    async def fetchone(self, sql: str, *params) -> dict | None:
        sql = _adapt_query(sql, use_postgres=False)
        with self._db.get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    async def execute(self, sql: str, *params) -> int:
        """Wykonuje INSERT/UPDATE/DELETE. Zwraca lastrowid lub rowcount."""
        sql = _adapt_query(sql, use_postgres=False)
        with self._db.get_conn() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid or cursor.rowcount

    async def executemany(self, sql: str, data: list[tuple]) -> None:
        sql = _adapt_query(sql, use_postgres=False)
        with self._db.get_conn() as conn:
            conn.executemany(sql, data)

    async def close(self) -> None:
        pass  # SQLite connections są per-request w istniejącym kodzie


# ── PostgreSQL adapter (asyncpg — Supabase) ───────────────────────────

class _PostgresDB:
    """Async adapter PostgreSQL przez asyncpg."""

    def __init__(self, conn):
        self._conn = conn

    async def fetchall(self, sql: str, *params) -> list[dict]:
        sql = _adapt_query(sql, use_postgres=True)
        rows = await self._conn.fetch(sql, *params)
        return [dict(r) for r in rows]

    async def fetchone(self, sql: str, *params) -> dict | None:
        sql = _adapt_query(sql, use_postgres=True)
        row = await self._conn.fetchrow(sql, *params)
        return dict(row) if row else None

    async def execute(self, sql: str, *params) -> int:
        sql = _adapt_query(sql, use_postgres=True)
        result = await self._conn.execute(sql, *params)
        # asyncpg zwraca "INSERT 0 1" — wyciągamy liczbę
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def executemany(self, sql: str, data: list[tuple]) -> None:
        sql = _adapt_query(sql, use_postgres=True)
        await self._conn.executemany(sql, data)

    async def close(self) -> None:
        pass  # zarządzane przez pool


# ── Pool PostgreSQL (singleton) ────────────────────────────────────────

_pg_pool = None


async def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        try:
            import asyncpg
        except ImportError:
            raise RuntimeError(
                "asyncpg nie jest zainstalowany. "
                "Uruchom: pip install asyncpg"
            )
        _pg_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size = 2,
            max_size = 10,
            command_timeout = 60,
        )
    return _pg_pool


async def close_pg_pool() -> None:
    """Zamknij pool przy shutdownie aplikacji."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None


# ── Migracje PostgreSQL ────────────────────────────────────────────────

_POSTGRES_SCHEMA = """
-- StockFlow PostgreSQL schema (Supabase)
-- Generowany automatycznie z backend/core/database.py

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist (
    user_id      TEXT NOT NULL DEFAULT 'default',
    ticker       TEXT NOT NULL,
    added_at     TEXT NOT NULL,
    last_score   REAL,
    last_checked TEXT,
    alert_high   REAL,
    alert_low    REAL,
    alert_crossover INTEGER DEFAULT 0,
    last_ma_state   TEXT,
    PRIMARY KEY (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS score_history (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    score  REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS scan_results (
    ticker     TEXT NOT NULL,
    name       TEXT,
    sector     TEXT,
    price      REAL,
    score      REAL,
    score_st   REAL,
    scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id          TEXT PRIMARY KEY,
    telegram_token   TEXT,
    telegram_chat_id TEXT,
    email_to         TEXT,
    email_smtp_server TEXT,
    email_smtp_port  INTEGER,
    email_user       TEXT,
    email_password   TEXT
);

CREATE TABLE IF NOT EXISTS alert_log (
    user_id    TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    date       TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    PRIMARY KEY (user_id, ticker, date, alert_type)
);

CREATE TABLE IF NOT EXISTS portfolio (
    id        SERIAL PRIMARY KEY,
    user_id   TEXT NOT NULL,
    ticker    TEXT NOT NULL,
    shares    REAL NOT NULL,
    buy_price REAL NOT NULL,
    buy_date  TEXT NOT NULL,
    notes     TEXT,
    added_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_cache (
    ticker    TEXT NOT NULL,
    period    TEXT NOT NULL,
    data      TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS journal (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    entry_date      TEXT NOT NULL,
    ticker          TEXT,
    decision        TEXT NOT NULL,
    reason          TEXT,
    score_at_entry  REAL,
    price_at_entry  REAL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def run_postgres_migrations(db: "_PostgresDB") -> None:
    """Wykonuje migracje na PostgreSQL przy starcie."""
    await db._conn.execute(_POSTGRES_SCHEMA)


# ── Public interface ───────────────────────────────────────────────────

Database = _SQLiteDB | _PostgresDB


@asynccontextmanager
async def get_db() -> AsyncGenerator[Database, None]:
    """
    FastAPI dependency — zwraca połączenie z bazą.

    Użycie:
        async with get_db() as db:
            rows = await db.fetchall("SELECT ...")

    Lub jako FastAPI dependency:
        @router.get("/...")
        async def endpoint(db: Annotated[Database, Depends(get_db_dep)]):
            ...
    """
    if settings.use_postgres:
        pool = await _get_pg_pool()
        async with pool.acquire() as conn:
            yield _PostgresDB(conn)
    else:
        yield _SQLiteDB()


async def get_db_dep() -> AsyncGenerator[Database, None]:
    """FastAPI Depends-compatible wrapper dla get_db."""
    async with get_db() as db:
        yield db


# ── Skrypt migracji SQLite → PostgreSQL ───────────────────────────────

async def migrate_sqlite_to_postgres(sqlite_path: str) -> dict:
    """
    Migruje dane z istniejącej bazy SQLite (Streamlit) do PostgreSQL (Supabase).

    Uruchom jednorazowo po skonfigurowaniu DATABASE_URL:
        python -m backend.core.database

    Zwraca dict z liczbą zmigrowanych rekordów per tabela.
    """
    import sqlite3

    if not settings.use_postgres:
        raise RuntimeError("DATABASE_URL nie jest ustawiony — brak celu migracji")

    # Źródło: SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Cel: PostgreSQL
    pool = await _get_pg_pool()
    counts: dict[str, int] = {}

    tables = [
        # (tabela, kolumny SQLite, kolumny PostgreSQL)
        ("watchlist",    None, None),
        ("score_history", None, None),
        ("scan_results", None, None),
        ("portfolio",    None, None),
        ("journal",      None, None),
        ("user_settings", None, None),
        ("alert_log",    None, None),
    ]

    async with pool.acquire() as pg_conn:
        # Upewnij się że schema istnieje
        await pg_conn.execute(_POSTGRES_SCHEMA)

        for (table, _, __) in tables:
            try:
                rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
            except sqlite3.OperationalError:
                counts[table] = 0
                continue

            if not rows:
                counts[table] = 0
                continue

            cols    = rows[0].keys()
            col_str = ", ".join(cols)
            placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))

            # Wyczyść przed insertem (idempotentna migracja)
            await pg_conn.execute(f"DELETE FROM {table}")

            data = [tuple(row) for row in rows]
            await pg_conn.executemany(
                f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})",
                data,
            )
            counts[table] = len(data)

    sqlite_conn.close()
    return counts


# ── CLI entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        sqlite_path = sys.argv[1] if len(sys.argv) > 1 else "./stock_app.db"
        print(f"Migracja: {sqlite_path} → PostgreSQL ({settings.database_url[:30]}...)")
        counts = await migrate_sqlite_to_postgres(sqlite_path)
        print("\nWynik migracji:")
        for table, count in counts.items():
            print(f"  {table:20s}: {count:5d} rekordów")
        total = sum(counts.values())
        print(f"\n  RAZEM: {total} rekordów zmigrowanych")
        await close_pg_pool()

    asyncio.run(main())
