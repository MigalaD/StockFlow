# Copyright (c) 2026 Damian Migała / StockFlow
# Wszystkie prawa zastrzeżone. All rights reserved.

"""
StockFlow FastAPI Backend
=========================
Uruchomienie lokalne:
  cd backend
  uvicorn main:app --reload --port 8000

Uruchomienie produkcyjne (Railway/Render):
  uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2

Dokumentacja API:
  http://localhost:8000/docs     (Swagger UI)
  http://localhost:8000/redoc    (ReDoc)

Zmienne środowiskowe (patrz backend/core/config.py):
  DATABASE_URL, SECRET_KEY, ALLOWED_ORIGINS, ...
"""

from __future__ import annotations

import sys
import os
import time

# Dodaj katalog projektu Streamlit do path — współdzielone moduły Python
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Rate limiting (slowapi) — współdzielony limiter z backend.core.limiter
from backend.core.limiter import limiter as _limiter, RATE_LIMITING_AVAILABLE as _rate_limiting_available
if _rate_limiting_available:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

import database as db
from backend.core.config import get_settings
from backend.core.database import (
    close_pg_pool,
    run_postgres_migrations,
    get_db,
)
from backend.routers.auth import router as auth_router
from backend.routers.analysis import router as analysis_router
from backend.routers.watchlist import router as watchlist_router
from backend.routers.portfolio import router as portfolio_router
from backend.routers.pdf import router as pdf_router
from backend.routers.forecast import router as forecast_router, news_router
from backend.routers.backtest import router as backtest_router
from backend.routers.scanner_journal import (
    scan_router,
    journal_router,
)
from backend.models.schemas import HealthResponse, InfoResponse
import external_data

settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicjalizacja przy starcie, sprzątanie przy zamknięciu."""
    # KRYTYCZNE: zwaliduj konfigurację produkcyjną zanim cokolwiek wstanie
    settings.validate_production_security()

    if settings.use_postgres:
        # PostgreSQL — uruchom migracje schematu
        async with get_db() as pg_db:
            from backend.core.database import run_postgres_migrations
            await run_postgres_migrations(pg_db)
        print(f"✅ PostgreSQL connected ({settings.database_url[:30]}...)")
    else:
        # SQLite — istniejący mechanizm migracji Streamlit
        db.init_db()
        db.run_migrations()
        print(f"✅ SQLite connected ({db.DB_PATH})")

    print(f"✅ StockFlow API v{settings.app_version} started")
    print(f"   Environment : {settings.environment}")
    print(f"   Database    : {'PostgreSQL/Supabase' if settings.use_postgres else 'SQLite (dev)'}")
    print(f"   CORS origins: {settings.allowed_origins}")
    yield
    # Shutdown
    if settings.use_postgres:
        await close_pg_pool()
    print("👋 StockFlow API shutting down")


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title       = settings.app_name,
    description = (
        "REST API dla StockFlow — narzędzia do analizy technicznej i fundamentalnej "
        "akcji, ETF-ów, kryptowalut i surowców.\n\n"
        "**Uwierzytelnienie:** Bearer JWT (POST /auth/login)\n\n"
        "**Endpointy publiczne** (bez tokenu): /analyze, /scan (GET), /health\n\n"
        "**Języki:** PL / EN (nagłówek Accept-Language)"
    ),
    version     = settings.app_version,
    lifespan    = lifespan,
    # Dokumentacja API tylko w dev — w produkcji ukryta (nie ujawniaj struktury API)
    docs_url    = "/docs"        if settings.environment != "production" else None,
    redoc_url   = "/redoc"       if settings.environment != "production" else None,
    openapi_url = "/openapi.json" if settings.environment != "production" else None,
)

# Rate limiter (opcjonalny — działa gdy slowapi zainstalowane)
if _rate_limiting_available:
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Middleware ────────────────────────────────────────────────────────

# CORS — Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.allowed_origins,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers     = ["Authorization", "Content-Type", "Accept-Language"],
    expose_headers    = ["X-Request-Time"],
)

# Kompresja GZIP dla dużych odpowiedzi (historia świec, wyniki skanu)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Security headers ──────────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Dodaje nagłówki bezpieczeństwa HTTP do każdej odpowiedzi."""
    response = await call_next(request)
    # Zapobiega MIME-sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Ochrona przed clickjacking (osadzaniem w iframe)
    response.headers["X-Frame-Options"] = "DENY"
    # Kontrola informacji w nagłówku Referer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Wyłącz niepotrzebne API przeglądarki
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # HSTS — wymuś HTTPS (tylko w produkcji, by nie utrudniać dev na http)
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Request timing middleware ─────────────────────────────────────────

@app.middleware("http")
async def add_request_time(request: Request, call_next):
    t0       = time.perf_counter()
    response = await call_next(request)
    elapsed  = round((time.perf_counter() - t0) * 1000, 1)
    response.headers["X-Request-Time"] = f"{elapsed}ms"
    return response


# ── Global error handlers ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if settings.environment == "development":
        detail = str(exc)
    else:
        detail = "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "type": type(exc).__name__},
    )


# ── Routers ───────────────────────────────────────────────────────────

API_V1 = "/api/v1"

app.include_router(auth_router,      prefix=API_V1)
app.include_router(analysis_router,  prefix=API_V1)
app.include_router(watchlist_router, prefix=API_V1)
app.include_router(portfolio_router, prefix=API_V1)
app.include_router(pdf_router,       prefix=API_V1)
app.include_router(forecast_router,  prefix=API_V1)
app.include_router(news_router,      prefix=API_V1)
app.include_router(backtest_router,  prefix=API_V1)
app.include_router(scan_router,      prefix=API_V1)
app.include_router(journal_router,   prefix=API_V1)


# ── Root endpoints ────────────────────────────────────────────────────

@app.get("/", response_model=InfoResponse, tags=["info"])
async def root() -> InfoResponse:
    """Informacje o API."""
    return InfoResponse(
        name    = settings.app_name,
        version = settings.app_version,
        docs    = "/docs",
        langs   = ["pl", "en"],
    )


@app.get("/health", response_model=HealthResponse, tags=["info"])
async def health() -> HealthResponse:
    """Health check — używany przez Railway/Render do monitorowania."""
    # Sprawdź DB
    try:
        db.get_last_scan_time()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    # Sprawdź zewnętrzne źródła
    sources = {}
    try:
        dom = external_data.get_btc_dominance()
        sources["coingecko"] = "ok" if dom else "unavailable"
    except Exception:
        sources["coingecko"] = "error"

    sources["binance"] = (
        "ok" if external_data.get_binance_price("BTC-USD") else "unavailable"
    )
    sources["alpaca"] = (
        "configured" if external_data.is_alpaca_configured() else "not_configured"
    )

    return HealthResponse(
        status  = "ok" if db_status == "ok" else "degraded",
        version = settings.app_version,
        db      = db_status,
        sources = sources,
    )
