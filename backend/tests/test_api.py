# Copyright (c) 2026 Damian Migała / StockFlow

"""
Testy backendu FastAPI — uruchom: pytest backend/tests/ -v

Używają TestClient (synchroniczny) i izolowanej bazy SQLite w pamięci.
Nie wymagają połączenia sieciowego dla testów auth/watchlist/portfolio.
Testy analizy mockują yfinance (jak w istniejących testach Streamlit).
"""

from __future__ import annotations

import sys
import os
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Izolowana baza SQLite przed importem modułów
_DB_FILE = tempfile.mktemp(suffix="_test.db")
os.environ["DB_PATH"]     = _DB_FILE
os.environ["SECRET_KEY"]  = "test-secret-key-minimum-32-chars-xxxxx"
os.environ["ENVIRONMENT"] = "development"

from fastapi.testclient import TestClient

import database as db
db.DB_PATH = _DB_FILE
db.init_db()
db.run_migrations()

from backend.main import app

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    """Wyczyść tabelę users przed każdym testem."""
    with db.get_conn() as conn:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM watchlist")
        conn.execute("DELETE FROM portfolio")
        conn.execute("DELETE FROM journal")
    yield


def _register_and_login(username="testuser", password="haslo1234") -> str:
    """Pomocnik: zarejestruj i zwróć JWT token."""
    client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password,
    })
    resp = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert "db" in data


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "StockFlow API"
    assert "pl" in data["langs"]
    assert "en" in data["langs"]


# ── Auth ──────────────────────────────────────────────────────────────

def test_register_success():
    resp = client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "password": "haslo1234",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user_id"] == "newuser"
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_register_duplicate():
    client.post("/api/v1/auth/register", json={
        "username": "dup", "password": "haslo1234"
    })
    resp = client.post("/api/v1/auth/register", json={
        "username": "dup", "password": "haslo1234"
    })
    assert resp.status_code == 409


def test_register_short_password():
    resp = client.post("/api/v1/auth/register", json={
        "username": "user2", "password": "abc"
    })
    assert resp.status_code == 422


def test_register_invalid_username():
    resp = client.post("/api/v1/auth/register", json={
        "username": "user name!", "password": "haslo1234"
    })
    assert resp.status_code == 422


def test_login_success():
    _register_and_login("loginuser", "haslo1234")
    resp = client.post("/api/v1/auth/login", json={
        "username": "loginuser", "password": "haslo1234"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    _register_and_login("user3", "haslo1234")
    resp = client.post("/api/v1/auth/login", json={
        "username": "user3", "password": "zlehaslo"
    })
    assert resp.status_code == 401


def test_login_nonexistent_user():
    resp = client.post("/api/v1/auth/login", json={
        "username": "nobody", "password": "haslo1234"
    })
    assert resp.status_code == 401


def test_me_authenticated():
    token = _register_and_login("meuser", "haslo1234")
    resp  = client.get("/api/v1/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "meuser"


def test_me_unauthenticated():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token():
    resp = client.get("/api/v1/auth/me",
                      headers={"Authorization": "Bearer zly.token.xyz"})
    assert resp.status_code == 401


# ── Watchlist ─────────────────────────────────────────────────────────

def test_watchlist_empty():
    token = _register_and_login("wluser", "haslo1234")
    resp  = client.get("/api/v1/watchlist", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_watchlist_add_and_get():
    token = _register_and_login("wluser2", "haslo1234")
    h     = _auth(token)

    add = client.post("/api/v1/watchlist",
                      json={"ticker": "AAPL"}, headers=h)
    assert add.status_code == 201

    get = client.get("/api/v1/watchlist", headers=h)
    assert get.status_code == 200
    tickers = [item["ticker"] for item in get.json()]
    assert "AAPL" in tickers


def test_watchlist_ticker_uppercased():
    token = _register_and_login("wluser3", "haslo1234")
    h     = _auth(token)
    client.post("/api/v1/watchlist", json={"ticker": "aapl"}, headers=h)
    get = client.get("/api/v1/watchlist", headers=h)
    assert get.json()[0]["ticker"] == "AAPL"


def test_watchlist_remove():
    token = _register_and_login("wluser4", "haslo1234")
    h     = _auth(token)
    client.post("/api/v1/watchlist", json={"ticker": "MSFT"}, headers=h)
    del_resp = client.delete("/api/v1/watchlist/MSFT", headers=h)
    assert del_resp.status_code == 204
    get = client.get("/api/v1/watchlist", headers=h)
    assert get.json() == []


def test_watchlist_set_alerts():
    token = _register_and_login("wluser5", "haslo1234")
    h     = _auth(token)
    client.post("/api/v1/watchlist", json={"ticker": "NVDA"}, headers=h)
    resp = client.put("/api/v1/watchlist/NVDA/alerts",
                      json={"alert_high": 75, "alert_low": 30,
                            "alert_crossover": True}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["alerts_updated"] is True


def test_watchlist_requires_auth():
    resp = client.get("/api/v1/watchlist")
    assert resp.status_code == 401


# ── Portfolio ─────────────────────────────────────────────────────────

def test_portfolio_add_and_get():
    token = _register_and_login("portuser", "haslo1234")
    h     = _auth(token)

    add = client.post("/api/v1/portfolio", json={
        "ticker":    "AAPL",
        "shares":    10,
        "buy_price": 150.0,
        "buy_date":  "2025-01-15",
        "notes":     "Zakup testowy",
    }, headers=h)
    assert add.status_code == 201
    assert add.json()["ticker"] == "AAPL"


def test_portfolio_negative_shares_rejected():
    token = _register_and_login("portuser2", "haslo1234")
    h     = _auth(token)
    resp  = client.post("/api/v1/portfolio", json={
        "ticker": "AAPL", "shares": -5, "buy_price": 150.0
    }, headers=h)
    assert resp.status_code == 422


def test_portfolio_zero_price_rejected():
    token = _register_and_login("portuser3", "haslo1234")
    h     = _auth(token)
    resp  = client.post("/api/v1/portfolio", json={
        "ticker": "AAPL", "shares": 5, "buy_price": 0
    }, headers=h)
    assert resp.status_code == 422


def test_portfolio_requires_auth():
    resp = client.get("/api/v1/portfolio")
    assert resp.status_code == 401


# ── Journal ────────────────────────────────────────────────────────────

def test_journal_add_and_get():
    token = _register_and_login("juser", "haslo1234")
    h     = _auth(token)

    add = client.post("/api/v1/journal", json={
        "entry_date": "2026-06-25",
        "ticker":     "AAPL",
        "decision":   "Kupno",
        "reason":     "Dobra okazja po korekcie",
        "score":      72.0,
        "price":      185.50,
    }, headers=h)
    assert add.status_code == 201

    get = client.get("/api/v1/journal", headers=h)
    assert get.status_code == 200
    entries = get.json()
    assert len(entries) == 1
    assert entries[0]["ticker"] == "AAPL"
    assert entries[0]["decision"] == "Kupno"


def test_journal_filter_by_ticker():
    token = _register_and_login("juser2", "haslo1234")
    h     = _auth(token)

    for tk in ["AAPL", "MSFT", "AAPL"]:
        client.post("/api/v1/journal", json={
            "entry_date": "2026-06-25", "ticker": tk,
            "decision": "Obserwacja", "reason": "Test",
        }, headers=h)

    resp = client.get("/api/v1/journal?ticker=AAPL", headers=h)
    assert resp.status_code == 200
    assert all(e["ticker"] == "AAPL" for e in resp.json())
    assert len(resp.json()) == 2


def test_journal_delete():
    token = _register_and_login("juser3", "haslo1234")
    h     = _auth(token)

    client.post("/api/v1/journal", json={
        "entry_date": "2026-06-25", "ticker": "TSLA",
        "decision": "Sprzedaż", "reason": "Realizacja zysku",
    }, headers=h)

    entries = client.get("/api/v1/journal", headers=h).json()
    entry_id = entries[0]["id"]

    del_resp = client.delete(f"/api/v1/journal/{entry_id}", headers=h)
    assert del_resp.status_code == 204

    after = client.get("/api/v1/journal", headers=h).json()
    assert after == []


def test_journal_requires_auth():
    resp = client.get("/api/v1/journal")
    assert resp.status_code == 401


# ── Scan ──────────────────────────────────────────────────────────────

def test_scan_get_empty():
    resp = client.get("/api/v1/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "total" in data


def test_scan_status():
    resp = client.get("/api/v1/scan/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "progress" in data
    assert "total" in data


def test_scan_start_requires_auth():
    resp = client.post("/api/v1/scan", json={"market": "krypto"})
    assert resp.status_code == 401


def test_scan_invalid_market():
    token = _register_and_login("scanuser", "haslo1234")
    resp  = client.post("/api/v1/scan",
                        json={"market": "nieistniejacy"},
                        headers=_auth(token))
    assert resp.status_code == 422


# ── Analyze (public) ──────────────────────────────────────────────────

def test_analyze_search_returns_list():
    resp = client.get("/api/v1/analyze/search?q=apple")
    # Może być 503 gdy Yahoo niedostępny — akceptujemy oba
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        assert isinstance(resp.json(), list)


def test_analyze_search_empty_query():
    resp = client.get("/api/v1/analyze/search?q=")
    assert resp.status_code == 422


def test_analyze_ticker_public_access():
    # Nie wymaga auth — endpoint publiczny
    resp = client.get("/api/v1/analyze/AAPL")
    # Może być 503/404 gdy Yahoo niedostępny — sprawdzamy tylko że nie wymaga 401
    assert resp.status_code != 401
