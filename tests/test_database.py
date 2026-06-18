"""
Testy dla database.py
========================
Każdy test dostaje czystą, tymczasową bazę SQLite (fixture `isolated_db`
z conftest.py), więc testy nie wpływają na realne dane i mogą się
wykonywać w dowolnej kolejności.
"""

import time

import pandas as pd


# ----------------------------------------------------------------------
# WATCHLIST
# ----------------------------------------------------------------------
def test_watchlist_add_remove(isolated_db):
    db = isolated_db

    db.add_to_watchlist("aapl", "alice")
    db.add_to_watchlist("MSFT", "alice")
    db.add_to_watchlist("AAPL", "bob")

    alice = db.get_watchlist("alice")
    bob = db.get_watchlist("bob")

    assert {e["ticker"] for e in alice} == {"AAPL", "MSFT"}
    assert {e["ticker"] for e in bob} == {"AAPL"}

    db.remove_from_watchlist("MSFT", "alice")
    alice = db.get_watchlist("alice")
    assert {e["ticker"] for e in alice} == {"AAPL"}

    # usuniecie u jednego usera nie wplywa na drugiego
    assert {e["ticker"] for e in db.get_watchlist("bob")} == {"AAPL"}


def test_watchlist_score_update_and_alerts(isolated_db):
    db = isolated_db

    db.add_to_watchlist("AAPL", "alice")
    db.update_watchlist_score("AAPL", 72.5, "alice")
    db.set_watchlist_alerts("AAPL", 80, 20, "alice")

    entry = db.get_watchlist("alice")[0]
    assert entry["last_score"] == 72.5
    assert entry["alert_high"] == 80
    assert entry["alert_low"] == 20


def test_get_all_watchlist_users(isolated_db):
    db = isolated_db
    db.add_to_watchlist("AAPL", "alice")
    db.add_to_watchlist("MSFT", "bob")

    users = set(db.get_all_watchlist_users())
    assert {"alice", "bob"}.issubset(users)


# ----------------------------------------------------------------------
# SCORE HISTORY
# ----------------------------------------------------------------------
def test_score_history(isolated_db):
    db = isolated_db
    db.save_score("AAPL", 60.0, day="2026-01-01")
    db.save_score("AAPL", 65.0, day="2026-01-02")
    db.save_score("AAPL", 65.0, day="2026-01-02")  # duplikat - powinien zastapic

    history = db.get_score_history("AAPL")
    assert len(history) == 2
    assert history[0]["date"] == "2026-01-01"
    assert history[-1]["score"] == 65.0


# ----------------------------------------------------------------------
# ALERT LOG
# ----------------------------------------------------------------------
def test_alert_log_dedup(isolated_db):
    db = isolated_db
    assert db.was_alert_sent_today("alice", "AAPL", "high") is False
    db.mark_alert_sent("alice", "AAPL", "high")
    assert db.was_alert_sent_today("alice", "AAPL", "high") is True
    # inny typ alertu jest niezalezny
    assert db.was_alert_sent_today("alice", "AAPL", "low") is False


# ----------------------------------------------------------------------
# PORTFOLIO
# ----------------------------------------------------------------------
def test_portfolio_crud(isolated_db):
    db = isolated_db
    db.add_position("alice", "AAPL", 5, 150.0, "2024-01-01", "long term")
    db.add_position("alice", "MSFT", 2, 300.0, "2024-02-01")

    positions = db.get_portfolio("alice")
    assert len(positions) == 2
    tickers = {p["ticker"] for p in positions}
    assert tickers == {"AAPL", "MSFT"}

    pos_id = positions[0]["id"]
    db.remove_position(pos_id, "alice")
    assert len(db.get_portfolio("alice")) == 1


# ----------------------------------------------------------------------
# PRICE CACHE
# ----------------------------------------------------------------------
def test_price_cache_set_get(isolated_db):
    db = isolated_db
    df = pd.DataFrame({"Close": [1.0, 2.0, 3.0]},
                       index=pd.date_range("2024-01-01", periods=3))
    data_json = df.to_json(orient="split", date_format="iso")

    assert db.get_price_cache("AAPL", "1y") is None

    db.set_price_cache("AAPL", "1y", data_json)
    cached = db.get_price_cache("AAPL", "1y")
    assert cached is not None
    import io
    restored = pd.read_json(io.StringIO(cached), orient="split")
    assert list(restored["Close"]) == [1.0, 2.0, 3.0]


def test_price_cache_expiry(isolated_db):
    db = isolated_db
    db.set_price_cache("AAPL", "1y", '{"data": []}')

    # max_age_seconds = 0 -> wpis natychmiast jest "stary"
    time.sleep(0.01)
    assert db.get_price_cache("AAPL", "1y", max_age_seconds=0) is None
    # duzy max_age -> wpis nadal swiezy
    assert db.get_price_cache("AAPL", "1y", max_age_seconds=3600) is not None


def test_price_cache_stats_and_clear(isolated_db):
    db = isolated_db
    db.set_price_cache("AAPL", "1y", '{"data": []}')
    db.set_price_cache("MSFT", "1y", '{"data": []}')

    stats = db.get_price_cache_stats()
    assert stats["n"] == 2

    db.clear_price_cache()
    stats = db.get_price_cache_stats()
    assert stats["n"] == 0


# ----------------------------------------------------------------------
# DZIENNIK INWESTYCYJNY
# ----------------------------------------------------------------------
def test_journal_crud(isolated_db):
    db = isolated_db
    db.add_journal_entry("alice", "2026-01-01", "AAPL", "Kupno",
                          "Dobry trend", score_at_entry=70.0, price_at_entry=150.0)
    db.add_journal_entry("alice", "2026-01-02", "MSFT", "Obserwacja", "")
    db.add_journal_entry("bob", "2026-01-01", "AAPL", "Sprzedaż", "")

    alice_entries = db.get_journal_entries("alice")
    assert len(alice_entries) == 2
    assert alice_entries[0]["entry_date"] == "2026-01-02"  # najnowsze pierwsze

    aapl_only = db.get_journal_entries("alice", ticker="AAPL")
    assert len(aapl_only) == 1
    assert aapl_only[0]["decision"] == "Kupno"
    assert aapl_only[0]["score_at_entry"] == 70.0

    db.delete_journal_entry(aapl_only[0]["id"], "alice")
    assert len(db.get_journal_entries("alice")) == 1

    # bob ma wlasny, niezalezny wpis
    assert len(db.get_journal_entries("bob")) == 1


# ----------------------------------------------------------------------
# USTAWIENIA (Telegram / E-mail)
# ----------------------------------------------------------------------
def test_telegram_settings(isolated_db):
    db = isolated_db
    assert db.get_telegram_settings("alice") is None

    db.save_telegram_settings("alice", "TOKEN123", "CHAT456")
    settings = db.get_telegram_settings("alice")
    assert settings["telegram_token"] == "TOKEN123"
    assert settings["telegram_chat_id"] == "CHAT456"

    all_users = db.get_all_telegram_users()
    assert any(u["user_id"] == "alice" for u in all_users)


def test_email_settings(isolated_db):
    db = isolated_db
    db.save_email_settings("alice", "smtp.gmail.com", 587, "a@x.com", "pass", "a@x.com")
    settings = db.get_email_settings("alice")
    assert settings["email_smtp_server"] == "smtp.gmail.com"
    assert settings["email_smtp_port"] == 587


# ----------------------------------------------------------------------
# MIGRACJE SCHEMATU
# ----------------------------------------------------------------------
def test_migration_adds_crossover_columns(isolated_db):
    db = isolated_db
    with db.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
    assert "alert_crossover" in cols
    assert "last_ma_state" in cols


def test_schema_version_recorded(isolated_db):
    db = isolated_db
    with db.get_conn() as conn:
        v = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    assert v["v"] >= 1


def test_migrations_idempotent(isolated_db):
    db = isolated_db
    # ponowne uruchomienie nie powinno rzucić ani zdublować wersji
    db.run_migrations()
    db.run_migrations()
    with db.get_conn() as conn:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
        versions = [r["version"] for r in rows]
    # każda wersja zastosowana dokładnie raz
    assert len(versions) == len(set(versions))


def test_crossover_alert_toggle(isolated_db):
    db = isolated_db
    db.add_to_watchlist("AAPL", "alice")
    db.set_crossover_alert("AAPL", True, "alice")
    entry = db.get_watchlist("alice")[0]
    assert entry["alert_crossover"] == 1

    db.set_crossover_alert("AAPL", False, "alice")
    entry = db.get_watchlist("alice")[0]
    assert entry["alert_crossover"] == 0


def test_update_ma_state(isolated_db):
    db = isolated_db
    db.add_to_watchlist("AAPL", "alice")
    db.update_ma_state("AAPL", "golden", "alice")
    entry = db.get_watchlist("alice")[0]
    assert entry["last_ma_state"] == "golden"


# ----------------------------------------------------------------------
# SZYFROWANIE SEKRETÓW + WAL
# ----------------------------------------------------------------------
def test_telegram_token_encrypted_at_rest(isolated_db):
    import sqlite3
    db = isolated_db
    db.save_telegram_settings("alice", "token-abc-123", "chat-1")
    # odczyt przez API daje odszyfrowaną wartość
    got = db.get_telegram_settings("alice")
    assert got["telegram_token"] == "token-abc-123"
    # bezpośredni odczyt z bazy pokazuje zaszyfrowaną wartość (prefiks enc::)
    raw = sqlite3.connect(db.DB_PATH).execute(
        "SELECT telegram_token FROM user_settings WHERE user_id='alice'"
    ).fetchone()[0]
    assert raw.startswith("enc::")
    assert raw != "token-abc-123"


def test_email_password_encrypted_at_rest(isolated_db):
    import sqlite3
    db = isolated_db
    db.save_email_settings("bob", "smtp.x.com", 587, "bob@x.com", "app-pass", "to@x.com")
    got = db.get_email_settings("bob")
    assert got["email_password"] == "app-pass"
    raw = sqlite3.connect(db.DB_PATH).execute(
        "SELECT email_password FROM user_settings WHERE user_id='bob'"
    ).fetchone()[0]
    assert raw.startswith("enc::")


def test_wal_mode_enabled(isolated_db):
    db = isolated_db
    with db.get_conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
